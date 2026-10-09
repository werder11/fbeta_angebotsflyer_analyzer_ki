# Deploying FlyerCheck to Cloud Run (target state)

> **Status: target-state instructions. None of this was executed in the PoC.** The PoC runs locally and in CI
> in `replay` mode only. Commands and flags reflect the intended setup from
> [deployment.md](../../docs/operations/deployment.md) and [ADR-0007](../../docs/adr/0007-modular-monolith-serverless.md);
> validate them against a sandbox project before relying on them. In production, Terraform should own these
> resources; the `gcloud` commands below document the shape of what Terraform creates.

One container image ([Dockerfile](../../Dockerfile)) serves two roles:

| Role | Cloud Run resource | Entry point |
|---|---|---|
| REST API (validations, findings, review decisions) | Service `flyercheck-api` | default `CMD`: `flyercheck serve --host 0.0.0.0 --port $PORT` |
| Batch validation of uploaded flyers | Job `flyercheck-validate` | `flyercheck run <pdf> --mode live --out <dir>` |

Note: in the PoC branch the API factory (`flyercheck.api.create_app`) is implemented by track E3; until it lands,
only the job role is functional.

## 0. Variables

```bash
export PROJECT_ID=my-gcp-project
export REGION=europe-west3                      # Frankfurt; EU-only data residency
export REPO=flyercheck
export IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/flyercheck:$(git rev-parse --short HEAD)
export RUNTIME_SA=flyercheck-runtime@$PROJECT_ID.iam.gserviceaccount.com
export BUCKET=$PROJECT_ID-flyercheck-inbox       # DTP export drop zone
export RESULTS_BUCKET=$PROJECT_ID-flyercheck-results

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com eventarc.googleapis.com workflows.googleapis.com pubsub.googleapis.com
```

## 1. Runtime identity and secret

```bash
gcloud iam service-accounts create flyercheck-runtime --display-name "FlyerCheck runtime"

# GEMINI_API_KEY lives only in Secret Manager (never in the image or env files).
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --replication-policy=user-managed \
  --locations=$REGION --data-file=-
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member=serviceAccount:$RUNTIME_SA --role=roles/secretmanager.secretAccessor
```

Target state per [ADR-0003](../../docs/adr/0003-provider-agnostic-llm-port.md): switch to Vertex AI Gemini in
`europe-west3` with Workload Identity (`roles/aiplatform.user` on the runtime SA), which removes the API key.

## 2. Build and push to Artifact Registry

```bash
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION \
  --description="FlyerCheck images"

# Either Cloud Build ...
gcloud builds submit --tag $IMAGE .
# ... or a local build
gcloud auth configure-docker $REGION-docker.pkg.dev
docker build -t $IMAGE . && docker push $IMAGE
```

## 3. API as a Cloud Run service (private, scale to zero)

```bash
gcloud run deploy flyercheck-api \
  --image=$IMAGE \
  --region=$REGION \
  --service-account=$RUNTIME_SA \
  --no-allow-unauthenticated \
  --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --min-instances=0 --max-instances=5 \
  --cpu=1 --memory=1Gi --concurrency=10 --timeout=300 \
  --port=8080

# Grant reviewers / the calling system access (IAP or an API gateway in front for humans).
gcloud run services add-iam-policy-binding flyercheck-api --region=$REGION \
  --member=group:flyer-reviewers@example.com --role=roles/run.invoker

# Smoke test with an identity token
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud run services describe flyercheck-api --region=$REGION --format='value(status.url)')/docs"
```

The container filesystem is ephemeral: `out/` is scratch space only. Runs, findings and review decisions belong
in Cloud SQL Postgres and GCS (see [deployment.md](../../docs/operations/deployment.md)).

## 4. Batch validation as a Cloud Run Job, triggered by GCS upload

Flow: DTP export → `gs://$BUCKET/*.pdf` → Eventarc (`google.cloud.storage.object.v1.finalized`) → Workflows →
`jobs.run` with the object name as an argument override → Job reads the PDF via a Cloud Storage FUSE volume and
writes `findings.json` + `report.html` to the results bucket.

```bash
gcloud storage buckets create gs://$BUCKET gs://$RESULTS_BUCKET --location=$REGION --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$RUNTIME_SA --role=roles/storage.objectViewer
gcloud storage buckets add-iam-policy-binding gs://$RESULTS_BUCKET \
  --member=serviceAccount:$RUNTIME_SA --role=roles/storage.objectAdmin

gcloud run jobs create flyercheck-validate \
  --image=$IMAGE \
  --region=$REGION \
  --service-account=$RUNTIME_SA \
  --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --add-volume=name=inbox,type=cloud-storage,bucket=$BUCKET,readonly=true \
  --add-volume-mount=volume=inbox,mount-path=/mnt/inbox \
  --add-volume=name=results,type=cloud-storage,bucket=$RESULTS_BUCKET \
  --add-volume-mount=volume=results,mount-path=/mnt/results \
  --cpu=2 --memory=2Gi --task-timeout=900 --max-retries=1 \
  --command=flyercheck \
  --args=run,/mnt/inbox/sample.pdf,--mode,live,--out,/mnt/results

# Manual run for one file
gcloud run jobs execute flyercheck-validate --region=$REGION \
  --args=run,/mnt/inbox/KW41.pdf,--mode,live,--out,/mnt/results
```

Workflow that starts the job once per uploaded object (save as `workflow.yaml`):

```yaml
# workflow.yaml
main:
  params: [event]
  steps:
    - run_job:
        call: googleapis.run.v1.namespaces.jobs.run
        args:
          name: ${"namespaces/" + sys.get_env("GOOGLE_CLOUD_PROJECT_ID") + "/jobs/flyercheck-validate"}
          location: europe-west3
          body:
            overrides:
              containerOverrides:
                - args: ["run", '${"/mnt/inbox/" + event.data.name}', "--mode", "live", "--out", "/mnt/results"]
```

```bash
gcloud workflows deploy flyercheck-on-upload --location=$REGION --source=workflow.yaml \
  --service-account=$RUNTIME_SA
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$RUNTIME_SA --role=roles/run.developer      # jobs.run with overrides
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$RUNTIME_SA --role=roles/eventarc.eventReceiver
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$RUNTIME_SA --role=roles/workflows.invoker
# GCS publishes via Pub/Sub under the hood: its service agent needs pubsub.publisher
GCS_SA=$(gcloud storage service-agent --project=$PROJECT_ID)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$GCS_SA --role=roles/pubsub.publisher

gcloud eventarc triggers create flyercheck-inbox-upload \
  --location=$REGION \
  --destination-workflow=flyercheck-on-upload --destination-workflow-location=$REGION \
  --event-filters=type=google.cloud.storage.object.v1.finalized \
  --event-filters=bucket=$BUCKET \
  --service-account=$RUNTIME_SA
```

Alternative without Workflows: a GCS → Pub/Sub notification consumed by a small push endpoint on the API service
that calls `jobs.run`. Workflows is preferred because it needs no extra code and retries declaratively.

## 5. Release gate before deploy

Deploys follow the CI gate in [.github/workflows/ci.yml](../../.github/workflows/ci.yml): lint → unit tests →
replay pipeline → `scripts/eval_gate.py` against the golden set → build/push → `gcloud run deploy`. A model or
prompt change requires a fresh `record` run and a reviewed eval diff ([ADR-0008](../../docs/adr/0008-evaluation-gated-replay.md)).
Use Workload Identity Federation for GitHub Actions (no service-account keys).

## Azure Container Apps (equivalent)

Same image; same split into an always-addressable app and an event-driven job.

```bash
export RG=rg-flyercheck LOC=germanywestcentral ACR=flyercheckacr ENV=cae-flyercheck
az group create -n $RG -l $LOC
az acr create -g $RG -n $ACR --sku Basic
az acr build -r $ACR -t flyercheck:$(git rev-parse --short HEAD) .
az containerapp env create -g $RG -n $ENV -l $LOC

# API: internal ingress, scale to zero, key from Key Vault via managed identity
az containerapp create -g $RG -n flyercheck-api --environment $ENV \
  --image $ACR.azurecr.io/flyercheck:<tag> --registry-server $ACR.azurecr.io \
  --system-assigned --ingress internal --target-port 8080 \
  --min-replicas 0 --max-replicas 5 \
  --secrets gemini-key=keyvaultref:https://<vault>.vault.azure.net/secrets/GEMINI-API-KEY,identityref:system \
  --env-vars GEMINI_API_KEY=secretref:gemini-key

# Batch: event-driven Container Apps Job scaled by a Service Bus queue fed by an Event Grid blob-created subscription
az containerapp job create -g $RG -n flyercheck-validate --environment $ENV \
  --image $ACR.azurecr.io/flyercheck:<tag> --trigger-type Event \
  --scale-rule-name blob-uploads --scale-rule-type azure-servicebus \
  --scale-rule-metadata queueName=flyer-uploads messageCount=1 \
  --command flyercheck --args "run" "/mnt/inbox/<file>.pdf" "--mode" "live" "--out" "/mnt/results"
```

On Azure the LLM port switches to Azure OpenAI (`--provider azure`, Germany West Central / Sweden Central), and the
blob is mounted via an Azure Files volume or fetched by a small wrapper; see
[deployment.md](../../docs/operations/deployment.md) for the full service mapping.
