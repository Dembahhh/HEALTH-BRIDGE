import { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { trackingApi } from '../services/api';
import TrendChart from '../components/analytics/TrendChart';
import NudgeCard from '../components/cards/NudgeCard';
import CheckInForm from '../features/tracking/CheckInForm';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LogCheckinPage() {
    const { user } = useSelector((state) => state.auth);
    const [trends, setTrends] = useState(null);
    const [latestNudge, setLatestNudge] = useState(null);

    const fetchData = async () => {
        try {
            const res = await trackingApi.getTrendsSummary();
            setTrends(res.data);
            const historyRes = await trackingApi.getHistory(null, 1);
            if (historyRes.data && historyRes.data.length > 0 && historyRes.data[0].nudge) {
                setLatestNudge(historyRes.data[0].nudge);
            }
        } catch (err) {
            console.error("Failed to load tracking data:", err);
        }
    };

    useEffect(() => {
        if (user?.uid) {
            fetchData();
        }
    }, [user]);

    // Format chart data from trends if available
    const chartData = trends?.bp?.history?.map(log => ({
        date: new Date(log.timestamp).toLocaleDateString([], { weekday: 'short' }),
        systolic: log.systolic,
        diastolic: log.diastolic
    })).reverse() || [];

    return (
        <div className="min-h-screen pb-20" style={{ background: 'var(--bg-primary)' }}>
            <header className="sticky top-0 z-50 px-4 py-4 flex items-center gap-4 bg-white/80 backdrop-blur-md border-b border-gray-100">
                <Link to="/dashboard" className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors">
                    <ArrowLeft className="w-5 h-5 text-gray-700" />
                </Link>
                <h1 className="text-xl font-bold text-gray-900">Check-In</h1>
            </header>

            <main className="max-w-lg mx-auto py-6 px-4 space-y-6">
                
                {/* 1. Nudge Card */}
                <div className="animate-fadeIn">
                    <NudgeCard nudge={latestNudge} />
                </div>

                {/* 2. Trend Chart */}
                <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-sm animate-fadeIn" style={{ animationDelay: '0.1s' }}>
                     <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-gray-900">7-Day Trends</h3>
                        <div className="text-xs text-gray-500 font-medium bg-gray-100 px-2 py-1 rounded-md">Blood Pressure</div>
                     </div>
                     <TrendChart 
                         data={chartData} 
                         dataKey="systolic" 
                         color="#ef4444" 
                         secondaryDataKey="diastolic" 
                         secondaryColor="#3b82f6" 
                     />
                </div>

                {/* 3. Check-in Form */}
                <div className="animate-fadeIn" style={{ animationDelay: '0.2s' }}>
                    <CheckInForm onLogSuccess={fetchData} />
                </div>
            </main>
        </div>
    );
}
