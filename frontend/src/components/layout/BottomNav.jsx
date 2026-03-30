import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, MessageSquare, User, Activity, Users } from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: Home },
  { name: 'Patients', path: '/patients', icon: Users },
  { name: 'Screening', path: '/screening', icon: Activity },
  { name: 'Coach', path: '/chat', icon: MessageSquare },
  { name: 'Profile', path: '/profile', icon: User },
];

const BottomNav = () => (
  <div className="fixed bottom-0 left-0 z-50 w-full h-16 bg-gray-900 border-t border-gray-700">
    <div className="grid h-full w-full grid-cols-5 mx-auto font-medium">
      {navItems.map(({ name, path, icon: Icon }) => (
        <NavLink
          key={name}
          to={path}
          end
          className={({ isActive }) =>
            `inline-flex flex-col items-center justify-center px-5 
             hover:bg-gray-800 group transition-colors 
             ${isActive ? 'text-blue-400' : 'text-gray-400'}`
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                className={`w-6 h-6 mb-1 ${isActive
                    ? 'text-blue-400'
                    : 'text-gray-500 group-hover:text-blue-400'
                  }`}
              />
              <span className={`text-xs ${isActive ? 'font-semibold' : ''}`}>
                {name}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </div>
  </div>
);

export default BottomNav;