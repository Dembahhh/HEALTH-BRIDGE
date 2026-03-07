# Frontend - Health-bridge AI

React frontend for the Health-bridge AI preventive health coach.

## Directory Structure

```
frontend/
├── src/
│   ├── components/      # UI Components
│   │   ├── ThemeToggle.jsx
│   │   ├── ErrorBoundary.jsx
│   │   └── LoadingIndicator.jsx
│   ├── context/         # React context providers
│   │   └── ThemeContext.jsx
│   ├── features/        # Redux slices
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── profile/
│   │   └── plans/
│   ├── pages/           # Route pages
│   │   ├── HomePage.jsx
│   │   ├── LoginPage.jsx
│   │   ├── SignupPage.jsx
│   │   ├── OnboardingPage.jsx
│   │   ├── ChatPage.jsx
│   │   └── DashboardPage.jsx
│   ├── services/        # API clients
│   │   ├── api.js
│   │   └── firebase.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── public/
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Setup

```bash
npm install
```

## Run Development Server

```bash
npm run dev
```

## Tech Stack

- **React 19** + **Vite** for fast development
- **TailwindCSS** for styling
- **Redux Toolkit** for state management
- **Firebase Auth** for authentication
- **Axios** for API calls
- **Lucide React** for icons
