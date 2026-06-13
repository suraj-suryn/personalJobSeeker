'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  Briefcase,
  CheckSquare,
  Mail,
  MessageSquare,
  BookOpen,
  Settings,
  LogOut,
  BriefcaseBusiness,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { logout } from '@/store/authSlice';
import { toggleSidebar } from '@/store/uiSlice';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/resumes', label: 'Resumes', icon: FileText },
  { href: '/jobs', label: 'Jobs', icon: Briefcase },
  { href: '/applications', label: 'Applications', icon: CheckSquare },
  { href: '/cover-letters', label: 'Cover Letters', icon: Mail },
  { href: '/outreach', label: 'Outreach', icon: MessageSquare },
  { href: '/interview-prep', label: 'Interview Prep', icon: BookOpen },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const router = useRouter();
  const open = useAppSelector((s) => s.ui.sidebarOpen);
  const user = useAppSelector((s) => s.auth.user);

  const handleLogout = () => {
    dispatch(logout());
    router.push('/login');
  };

  return (
    <aside
      className={cn(
        'flex flex-col bg-gray-900 text-white transition-all duration-200 flex-shrink-0',
        open ? 'w-56' : 'w-14'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-gray-700">
        <div className="bg-brand-500 text-white p-1.5 rounded-lg flex-shrink-0">
          <BriefcaseBusiness size={20} />
        </div>
        {open && (
          <span className="font-bold text-sm truncate">PersonalJobSeeker</span>
        )}
        <button
          onClick={() => dispatch(toggleSidebar())}
          className="ml-auto text-gray-400 hover:text-white"
        >
          {open ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors',
                active
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
              title={!open ? label : undefined}
            >
              <Icon size={18} className="flex-shrink-0" />
              {open && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User + Logout */}
      <div className="border-t border-gray-700 p-3">
        {open && user && (
          <div className="mb-2 px-2">
            <p className="text-sm font-medium truncate">{user.name}</p>
            <p className="text-xs text-gray-400 truncate">{user.role}</p>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white w-full transition-colors"
          title={!open ? 'Sign out' : undefined}
        >
          <LogOut size={18} className="flex-shrink-0" />
          {open && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}
