# IAM policies (manual reference)

Terraform in `infra/terraform/shared` creates all of these for you. These JSON files exist so you can
read them, learn what each permission does, or attach them by hand in the console.

| File | Attach to | Purpose |
|---|---|---|
| `bedrock-policy.json` | IAM user (local dev) or app role | Call Nova + Titan through Bedrock. Nothing else. |
| `s3-datasets-policy.json` | App role | Read/write CSVs under `datasets/` in one bucket |
| `github-oidc-trust-policy.json` | CI role (trust policy) | Let GitHub Actions on `main` assume the role with no stored keys |

Replace `YOUR_ACCOUNT_ID` / `YOUR_BUCKET` before use.

`us.amazon.nova-*` IDs are cross-region inference profiles: Bedrock may serve a call from us-east-1,
us-east-2 or us-west-2, which is why both the profile ARN and the foundation-model ARNs (any region) are allowed.
