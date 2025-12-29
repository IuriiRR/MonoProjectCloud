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

### Firebase Auth

Google Login and Email/Password are supported via the Firebase Auth Emulator. 
- When running locally, the React app automatically connects to the emulator on port `9099`.
- You can manage users and see sign-in logs in the Emulator UI at `http://localhost:4000/auth`.
- For Google Auth, the emulator will show a "mock" sign-in popup where you can choose any email to log in.


