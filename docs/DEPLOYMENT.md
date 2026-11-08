# Deploying InsightPilot

One application, four ways to run it. Each path reuses the same container images and the same IAM policy.

```
                 GitHub (push to main)
                        |
          CI: lint, tests, image build, smoke test, Trivy scan
                        |
       Release: OIDC -> AWS, push images to ECR, deploy
                        |
     +------------------+-------------------+------------------+
     |                  |                   |                  |
  local compose      EC2 + compose      ECS Fargate + ALB     EKS (Kubernetes)
  (your laptop)      (1 VM, SSM)        (+ RDS, Secrets Mgr)  (Pod Identity, HPA)
```

| Path | Folder | What you learn | Approx. cost while running |
|---|---|---|---|
| Docker Compose | `docker-compose.yml` | images, networks, volumes, health checks | free |
| EC2 | `infra/terraform/ec2`, `infra/ec2` | VMs, security groups, instance profiles, IMDSv2, SSM | free tier (t3.micro) |
| ECS Fargate | `infra/terraform/ecs` | task definitions, task vs execution roles, ALB, RDS, Secrets Manager, autoscaling, rollbacks | ~$1/day (ALB + RDS + Fargate) |
| EKS | `infra/eks`, `infra/k8s` | pods, deployments, services, probes, HPA, PVCs, Pod Identity, access entries | ~$3.50/day (control plane + spot nodes + LB) |

> **Tear down after every session.** Load balancers, RDS and the EKS control plane bill by the hour
> even when idle. Teardown commands are at the end of each section.

---

## 0. One-time setup

### Tools
| Tool | Needed for | Install (Windows) |
|---|---|---|
| Docker Desktop | everything | https://www.docker.com/products/docker-desktop |
| AWS CLI v2 | AWS paths | `winget install Amazon.AWSCLI` |
| Terraform ≥ 1.6 | EC2, ECS | `winget install Hashicorp.Terraform` |
| kubectl, eksctl | EKS | `winget install Kubernetes.kubectl` and `winget install eksctl` |

### AWS credentials for provisioning
The Bedrock API key in `backend/.env` can only call Bedrock. Creating infrastructure needs normal IAM
credentials:

1. In IAM, create a user for yourself (e.g. `sourabh-admin`) with `AdministratorAccess`, and enable MFA.
2. Create an access key for it, then run `aws configure` (region `us-east-1`).
3. Check: `aws sts get-caller-identity`

The running application never uses these keys. On AWS it gets temporary credentials from an IAM role.

### Bedrock model access
In the Bedrock console (us-east-1), confirm **Amazon Nova Lite** and **Titan Text Embeddings V2** are enabled.

---

## 1. Local: Docker Compose

```bash
docker compose up --build        # http://localhost:8080
docker compose down              # stop (add -v to delete the Postgres volume)
```

To use Bedrock locally, create a `.env` in the repo root (same keys as `backend/.env`).

---

## 2. Shared AWS resources (do this once)

```bash
cd infra/terraform/shared
terraform init
terraform apply
```

This creates:
- two ECR repositories (`insightpilot-api`, `insightpilot-web`)
- the datasets S3 bucket, with the sample CSVs uploaded
- the `insightpilot-app` IAM policy (Bedrock + S3)
- the GitHub OIDC provider and the `insightpilot-github-ci` role

> If `terraform apply` says the OIDC provider already exists, run
> `terraform apply -var create_github_oidc_provider=false`.

### Connect GitHub Actions
In the GitHub repo, open Settings → Secrets and variables → Actions → **Variables** and add:

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `terraform output -raw ci_role_arn` |
| `AWS_REGION` | `us-east-1` |
| `DEPLOY_TARGET` | `none` for now |

Push any commit (or run **Release** manually from the Actions tab). Images land in ECR tagged with the
git SHA and `latest`. There are no AWS keys in GitHub: the workflow exchanges a short-lived OIDC
token for role credentials.

---

## 3. EC2: one VM with Docker Compose

```bash
cd infra/terraform/ec2
terraform init
terraform apply                  # optional: -var 'allowed_cidrs=["<your-ip>/32"]'
terraform output url             # wait ~3 minutes for first boot
```

What happens: Amazon Linux 2023 boots, `user_data` installs Docker, writes
`/opt/insightpilot/{docker-compose.yml,.env,deploy.sh}`, logs in to ECR with the instance role, and
starts Postgres, the API and nginx.

- **Shell without SSH:** `terraform output -raw shell`, then run what it prints
  (needs the Session Manager plugin for the AWS CLI).
- **Logs:** `sudo docker compose -f /opt/insightpilot/docker-compose.yml logs -f api`
- **Continuous deployment:** set `DEPLOY_TARGET=ec2`. Each push to `main` builds new images, then runs
  `deploy.sh <git-sha>` on the instance through SSM Run Command.
- **Teardown:** `terraform destroy`

---

## 4. ECS Fargate: serverless containers behind a load balancer

```bash
cd infra/terraform/ecs
terraform init
terraform apply                  # ~10 min (RDS is the slow part)
terraform output url
```

Architecture:
- **Networking:** a new VPC with 2 public subnets. There's no NAT gateway; tasks get public IPs but
  only accept traffic from the ALB's security group.
- **One task, two containers:** `web` (nginx) and `api` (FastAPI). nginx reaches the API at
  `localhost:8000`, and `web` only starts once `api` passes its health check.
- **Database:** RDS PostgreSQL 16 (pgvector) with the connection string in Secrets Manager. The
  *execution role* reads the secret; the *task role* calls Bedrock and S3.
- **Safety and scaling:** a deployment circuit breaker automatically rolls back failed deploys, and
  CPU target tracking scales from 1 to 3 tasks.

Useful commands:
```bash
terraform output -raw tail_logs | sh        # stream CloudWatch logs
aws ecs describe-services --cluster insightpilot --services insightpilot \
  --query "services[0].deployments"          # watch a rollout
```

- **Continuous deployment:** set `DEPLOY_TARGET=ecs`. Each push to `main` registers a new task
  definition revision with the git-SHA images and waits until the service is stable.
- **Cheaper variant:** `terraform apply -var enable_rds=false` uses SQLite inside the task (history is
  lost on each deploy).
- **Teardown:** `terraform destroy`

---

## 5. EKS: Kubernetes

1. **Create the cluster** (~15 min). In `infra/eks/cluster.yaml`, replace `YOUR_ACCOUNT_ID`, then run:
   ```bash
   eksctl create cluster -f infra/eks/cluster.yaml
   kubectl get nodes
   ```
2. **Configure the manifests.** In `infra/k8s/kustomization.yaml`, replace `YOUR_ACCOUNT_ID` (bucket
   name and image registry). Then create the secrets file and edit both lines:
   ```bash
   cp infra/k8s/secrets.env.example infra/k8s/secrets.env
   ```
3. **Deploy:**
   ```bash
   kubectl apply -k infra/k8s
   kubectl -n insightpilot get pods -w
   kubectl -n insightpilot get svc web       # EXTERNAL-IP = load balancer hostname (~2 min)
   ```

What's inside:
- **Workloads:** `api` (2 to 5 replicas with an HPA, rolling updates with zero unavailable, startup,
  liveness and readiness probes), `web` (2 replicas behind a `LoadBalancer` Service) and `postgres`
  (a StatefulSet with a gp3 EBS volume).
- **AWS access:** EKS Pod Identity maps the `insightpilot-api` service account to an IAM role with the
  app policy, so there are no keys in the cluster.
- **Who can deploy:** an EKS access entry lets the CI role edit only the `insightpilot` namespace.

Debugging:
```bash
kubectl -n insightpilot logs deploy/api -f
kubectl -n insightpilot describe pod <name>
kubectl -n insightpilot exec -it deploy/api -- python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

- **Continuous deployment:** set `DEPLOY_TARGET=eks`. CI runs `kubectl set image` with the git-SHA
  tag and waits for the rollout to finish.
- **Teardown:** `kubectl delete -k infra/k8s`, then `eksctl delete cluster -f infra/eks/cluster.yaml`

---

## 6. Cleaning up everything

```bash
kubectl delete -k infra/k8s; eksctl delete cluster -f infra/eks/cluster.yaml   # if EKS is up
(cd infra/terraform/ecs && terraform destroy)
(cd infra/terraform/ec2 && terraform destroy)
(cd infra/terraform/shared && terraform destroy)   # last: removes ECR, the bucket and IAM
```

Afterwards, check the Billing console the next day. Also check EC2 → Load Balancers and EBS → Volumes
for leftovers from Kubernetes Services or PVCs that were deleted out of order.
