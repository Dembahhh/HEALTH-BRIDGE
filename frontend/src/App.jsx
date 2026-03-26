import { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { initAuthListener } from './features/auth/authSlice';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import OnboardingPage from './pages/OnboardingPage';
import LoadingIndicator from './components/LoadingIndicator';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const LogCheckinPage = lazy(() => import('./pages/LogCheckinPage'));
const ScreeningPage = lazy(() => import('./pages/ScreeningPage'));
const PatientViewPage = lazy(() => import('./pages/PatientViewPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));

// Protected Route Wrapper
import BottomNav from './components/layout/BottomNav';

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useSelector((state) => state.auth);
    const location = useLocation();

    if (loading) {
        return <LoadingIndicator />;
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return (
        <>
            {children}
            {/* Show bottom navigation ONLY on protected pages, excluding onboarding  */}
            {location.pathname !== '/onboarding' && <BottomNav />}
        </>
    );
};

// Redirect component to handle root path logic securely
const RootRedirect = () => {
    const { isAuthenticated } = useSelector((state) => state.auth);
    return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />;
};

function App() {
    const dispatch = useDispatch();
    const { loading } = useSelector((state) => state.auth);

    useEffect(() => {
        initAuthListener(dispatch);
    }, [dispatch]);

    if (loading) {
        return <LoadingIndicator />;
    }

    return (
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
                            <Suspense fallback={<LoadingIndicator />}>
                                <DashboardPage />
                            </Suspense>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/log"
                    element={
                        <ProtectedRoute>
                            <Suspense fallback={<LoadingIndicator />}>
                                <LogCheckinPage />
                            </Suspense>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/screening"
                    element={
                        <ProtectedRoute>
                            <Suspense fallback={<LoadingIndicator />}>
                                <ScreeningPage />
                            </Suspense>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/patients"
                    element={
                        <ProtectedRoute>
                            <Suspense fallback={<LoadingIndicator />}>
                                <PatientViewPage />
                            </Suspense>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/profile"
                    element={
                        <ProtectedRoute>
                            <Suspense fallback={<LoadingIndicator />}>
                                <ProfilePage />
                            </Suspense>
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </Router>
    );
}

export default App;
