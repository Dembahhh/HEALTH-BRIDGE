import { useEffect, Suspense, lazy } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { initAuthListener } from "./features/auth/authSlice";
import HomePage from "./pages/HomePage";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import OnboardingPage from "./pages/OnboardingPage";
import LoadingIndicator from "./components/LoadingIndicator";
import BottomNav from "./components/layout/BottomNav";
import { LitProvider } from "./context/LitContext";
import PageSkeleton from "./components/PageSkeleton";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const LogCheckinPage = lazy(() => import("./pages/LogCheckinPage"));
const ScreeningPage = lazy(() => import("./pages/ScreeningPage"));
const PatientViewPage = lazy(() => import("./pages/PatientViewPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));

// Protected Route Wrapper

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useSelector((state) => state.auth);
  const location = useLocation();

  if (loading) {
    return <PageSkeleton />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  //don't show nav on onboarding
  const showNav = location.pathname !== "/onboarding";

  return (
    <div className="flex flex-col min-h-screen">
      <main className={`flex-1 ${showNav ? "pb-16" : ""}`}>{children}</main>
      {showNav && <BottomNav />}
    </div>
  );
};

// Redirect component to handle root path logic securely
const RootRedirect = () => {
  const { isAuthenticated, loading } = useSelector((state) => state.auth);

  if (loading) {
    return <PageSkeleton />;
  }
  return isAuthenticated ? (
    <Navigate to="/dashboard" replace />
  ) : (
    <Navigate to="/login" replace />
  );
};

function App() {
  const dispatch = useDispatch();
  const { loading } = useSelector((state) => state.auth);

  useEffect(() => {
    initAuthListener(dispatch);
  }, [dispatch]);

  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <LitProvider>
      <Router>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Protected Routes */}
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <OnboardingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSkeleton />}>
                  <DashboardPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/log"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSkeleton />}>
                  <LogCheckinPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/screening"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSkeleton />}>
                  <ScreeningPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/patients"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSkeleton />}>
                  <PatientViewPage />
                </Suspense>
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Suspense fallback={<PageSkeleton />}>
                  <ProfilePage />
                </Suspense>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </LitProvider>
  );
}

export default App;
