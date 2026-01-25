import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchProfile } from '../features/profile/profileSlice';
import { logout } from '../features/auth/authSlice';
import ProfileForm from '../features/profile/ProfileForm';
import { Link, useNavigate } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';

export default function DashboardPage() {
  const dispatch = useDispatch();
  // useTheme hook is now used inside ThemeToggle, but we might still need theme for other conditional rendering if any
  // But strictly for the toggle, we can remove it from here if not used elsewhere. 
  // Wait, local usage: {theme === 'dark' ? <Sun...} was replaced.
  const { user } = useSelector((state) => state.auth);
  const { data: profile, loading } = useSelector((state) => state.profile);
  const [isEditing, setIsEditing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(fetchProfile());
  }, [dispatch]);

  console.log('Dashboard State:', { loading, profile, skipped: localStorage.getItem('onboarding_skipped') });

  // Redirect to onboarding if profile is incomplete and not skipped
  // Redirect to onboarding if profile is incomplete and not skipped
  useEffect(() => {
    if (!loading && user?.uid) {
      const skipKey = `onboarding_skipped_${user.uid}`;
      const isSkipped = localStorage.getItem(skipKey);

      if (profile) {
        // Check if essential fields are missing. 
        if (!profile.age_band && !isSkipped) {
          navigate('/onboarding');
        }
      } else {
        // Profile not found at all
        if (!isSkipped) {
          navigate('/onboarding');
        }
      }
    }
  }, [loading, profile, navigate, user]);

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
      <nav className="bg-white dark:bg-gray-800 shadow transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-bold text-gray-800 dark:text-white">HealthBridge</span>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggle />

              {user?.photoURL ? (
                <img className="h-10 w-10 rounded-full object-cover border-2 border-gray-200 dark:border-gray-600" src={user.photoURL} alt={user.displayName} />
              ) : (
                <div className="h-10 w-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-lg border-2 border-white dark:border-gray-600 shadow-sm">
                  {user?.displayName ? user.displayName.charAt(0).toUpperCase() : (user?.email ? user.email.charAt(0).toUpperCase() : '?')}
                </div>
              )}
              <span className="text-gray-700 dark:text-gray-200 font-medium hidden sm:block">{user?.displayName || user?.email}</span>
              <button onClick={handleLogout} className="text-sm text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 font-semibold px-3 py-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">Logout</button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">

          {!profile && !loading && (
            <div className="mb-6 bg-yellow-50 dark:bg-yellow-900/30 border-l-4 border-yellow-400 p-4">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-yellow-700 dark:text-yellow-200">
                    Please complete your profile to start your assessment.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

            {/* Action Card */}
            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg transition-colors duration-200">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">Assessment</h3>
                <div className="mt-2 max-w-xl text-sm text-gray-500 dark:text-gray-400">
                  <p>Start a conversation with your AI health coach.</p>
                </div>
                <div className="mt-5">
                  <Link to="/chat" className="inline-flex items-center justify-center px-4 py-2 border border-transparent font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 sm:w-auto sm:text-sm transition-colors">
                    Start Assessment
                  </Link>
                </div>
              </div>
            </div>

            {/* Profile Section */}
            <div className="space-y-6">
              {(isEditing || !profile) ? (
                <ProfileForm existingProfile={profile} onSuccess={() => setIsEditing(false)} />
              ) : (
                <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg transition-colors duration-200">
                  <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">Profile Summary</h3>
                    <button onClick={() => setIsEditing(true)} className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300">Edit</button>
                  </div>
                  <div className="border-t border-gray-200 dark:border-gray-700">
                    <dl>
                      <div className="bg-gray-50 dark:bg-gray-900/50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                        <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Age Band</dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 sm:mt-0 sm:col-span-2">{profile.age_band}</dd>
                      </div>
                      <div className="bg-white dark:bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                        <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Sex</dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 sm:mt-0 sm:col-span-2 capitalize">{profile.sex}</dd>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-900/50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                        <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Family History</dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 sm:mt-0 sm:col-span-2">
                          {[
                            profile.family_history_hypertension && 'Hypertension',
                            profile.family_history_diabetes && 'Diabetes'
                          ].filter(Boolean).join(', ') || 'None reported'}
                        </dd>
                      </div>
                      <div className="bg-white dark:bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                        <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Lifestyle</dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 sm:mt-0 sm:col-span-2 capitalize">
                          <span className="block"><span className="font-medium">Smoking:</span> {profile.smoking_status}</span>
                          <span className="block"><span className="font-medium">Alcohol:</span> {profile.alcohol_consumption}</span>
                        </dd>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-900/50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                        <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Activity Level</dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 sm:mt-0 sm:col-span-2 capitalize">{profile.activity_level}</dd>
                      </div>
                    </dl>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
