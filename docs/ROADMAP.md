# Deployment roadmap

InsightPilot was built so one real application can be taken through every common deployment path. Each stage
builds on the previous one. Tick them off as you go. All the configuration already exists in this repo;
the commands are in **[DEPLOYMENT.md](DEPLOYMENT.md)**. The goal is to run each stage yourself and
understand every line.

> **Cost discipline:** tear down cloud resources at the end of every session (`terraform destroy`, or delete
> the stack). The things that bill even when idle are NAT gateways, load balancers, EKS control planes and
> RDS instances.

## Stage 0: Run locally (done)
- [x] Backend with the offline fake LLM, frontend with the Vite dev server
- [x] Switch to real Bedrock (`LLM_PROVIDER=bedrock`)
- [ ] Compare Nova Lite and Nova Pro on cost and answer quality

## Stage 1: Containers
- [ ] Install Docker Desktop and understand images, layers, multi-stage builds and non-root users
- [ ] `docker build` the API and web images and inspect their sizes
- [ ] `docker compose up`: networking between services, volumes, health checks, `depends_on`
- [ ] Debug: `docker logs`, `docker exec`, `docker stats`

## Stage 2: CI with GitHub Actions
- [ ] Workflow: ruff, pytest, `tsc` on every pull request
- [ ] Build both images in CI with layer caching
- [ ] Image vulnerability scan (Trivy)
- [ ] Branch protection: CI must pass before merge

## Stage 3: AWS foundations
- [ ] IAM: users vs roles, least-privilege policy for Bedrock + S3
- [ ] Amazon ECR: push images, lifecycle policies
- [ ] Use **OIDC** so GitHub Actions can push to ECR without long-lived keys
- [ ] S3 bucket for datasets (`STORAGE_BACKEND=s3`)

## Stage 4: EC2
- [ ] Launch an instance, security groups, SSH / SSM Session Manager
- [ ] Instance profile (IAM role) for Bedrock, with no keys on the box
- [ ] Run with docker compose; then add a CD job that deploys on every push to `main`
- [ ] Optional: Elastic IP, domain name and HTTPS via Caddy or nginx + Let's Encrypt

## Stage 5: ECS Fargate
- [ ] Task definitions, services, task roles vs execution roles
- [ ] Application Load Balancer, target groups, health checks (`/readyz`)
- [ ] Amazon RDS for PostgreSQL + pgvector, with secrets in Secrets Manager
- [ ] CloudWatch Logs (the JSON logs), alarms, autoscaling on CPU or request count
- [ ] Blue/green or rolling deploys from GitHub Actions

## Stage 6: Infrastructure as Code
- [ ] Terraform: VPC, ECR, ECS, ALB, RDS, IAM as modules
- [ ] Remote state in S3 with locking
- [ ] `plan` on pull requests, `apply` on merge

## Stage 7: EKS (Kubernetes)
- [ ] Cluster with eksctl or Terraform; understand nodes, pods, deployments and services
- [ ] Manifests, then a Helm chart for API + web; probes on `/healthz` and `/readyz`
- [ ] IRSA / Pod Identity for Bedrock and S3 access
- [ ] AWS Load Balancer Controller + Ingress, HPA autoscaling
- [ ] ConfigMaps and Secrets (External Secrets Operator)
- [ ] GitOps with Argo CD

## Stage 8: Production polish
- [ ] Prometheus + Grafana (or Amazon Managed Prometheus) scraping `/metrics`
- [ ] Alembic database migrations as a deploy step
- [ ] Rate limiting, the `API_KEY` header, or Cognito auth
- [ ] Load testing (k6 / Locust) and cost-per-question dashboards
