## CloudApi (local dev)

### Services

- **Firestore Emulator**: `http://localhost:4000/firestore` (UI), `localhost:8080` (API)
- **Auth Emulator**: `http://localhost:4000/auth` (UI), `localhost:9099` (API)
- **Frontend (React)**: `http://localhost:3000`
- **Users API**: `http://localhost:8081`
- **Accounts API**: `http://localhost:8082`
- **Transactions API**: `http://localhost:8083`

### Running locally

To start everything (backend services, firestore emulator, and frontend):

```bash
make run
```

Or manually via docker-compose:

```bash
docker compose up --build
```

### Frontend Development

The frontend is a React app located in the `frontend/` directory.

```bash
cd frontend
npm install
npm run dev
```

### Testing

Run both backend and frontend tests:

```bash
make test
```

### Deployment (GCP & Firebase)

The project is configured for deployment to GCP (Cloud Functions) and Firebase Hosting.

1. **Deploy Backend (GCP)**:
   ```bash
   cd tf
   terraform init
   terraform apply
   ```
   *Note: Ensure you have `terraform.tfvars` populated with your `project_id` and other required variables.*
   
   If `terraform apply` fails when enabling APIs with `AUTH_PERMISSION_DENIED`, you need a role like **Project Owner** or **Service Usage Admin** (`roles/serviceusage.serviceUsageAdmin`) on the GCP project (or ask a project admin to enable the required APIs once in the console).

   For **Google Login** in production, you must enable it either:
   - In **Firebase Console**: Authentication → Sign-in method → enable Google, and ensure Authorized domains include `${project_id}.web.app`
   - Or via **Terraform** by setting `google_oauth_client_id` / `google_oauth_client_secret` in `tf/terraform.tfvars` (see `tf/terraform.tfvars.example`).

2. **Deploy Frontend (Firebase)**:
   A helper script is provided to automate the frontend build and deployment:
   ```bash
   ./scripts/deploy_frontend.sh
   ```
   *Note: You will need to have the `firebase-tools` CLI installed and authenticated (`firebase login`).*

   If you update anything under `tf/` (like outputs/resources), re-run `terraform apply` before deploying the frontend. The script relies on Terraform outputs like `firebase_web_config`.

### Firebase Auth Emulator

Google Login and Email/Password are supported via the Firebase Auth Emulator. 
- When running locally, the React app automatically connects to the emulator on port `9099`.
- You can manage users and see sign-in logs in the Emulator UI at `http://localhost:4000/auth`.
- For Google Auth, the emulator will show a "mock" sign-in popup where you can choose any email to log in.


