import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, MessageSquare, User } from 'lucide-react';

const BottomNav = () => {
  const location = useLocation();

  // Highlight rules based on exact or partial paths
  const navItems = [
    {
       name: 'Dashboard',
       path: '/dashboard',
       icon: Home,
    },
    {
       name: 'Coach',
       path: '/chat',
       icon: MessageSquare,
    },
    {
       name: 'Profile',
       path: '/settings',
       icon: User,
    }
  ];

  return (
    <div className="fixed bottom-0 left-0 z-50 w-full h-16 bg-white border-t border-gray-200">
      <div className="grid h-full max-w-lg grid-cols-3 mx-auto font-medium">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={`inline-flex flex-col items-center justify-center px-5 hover:bg-gray-50 group transition-colors ${
                isActive ? 'text-primary-600' : 'text-gray-500'
              }`}
            >
              <item.icon
                className={`w-6 h-6 mb-1 ${isActive ? 'text-primary-600' : 'text-gray-400 group-hover:text-primary-600'}`}
              />
              <span className={`text-xs ${isActive ? 'font-semibold' : ''}`}>
                {item.name}
              </span>
            </NavLink>
          );
        })}
      </div>
    </div>
  );
};

export default BottomNav;
