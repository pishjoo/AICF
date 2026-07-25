'use client';

import { Bell, Moon, Sun, User, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  // Placeholder for theme toggle - will be functional when next-themes is installed
  const toggleTheme = () => {
    console.log('Theme toggle clicked - install next-themes to enable');
  };

  return (
    <header
      className={cn(
        'h-16 bg-white border-b flex items-center justify-between px-6',
        className
      )}
    >
      {/* Left side - could include breadcrumbs or page title */}
      <div className="flex items-center gap-4">
        <span className="text-lg font-semibold text-gray-900">
          AICF v2 Dashboard
        </span>
      </div>

      {/* Right side - Actions */}
      <div className="flex items-center gap-4">
        {/* Notification button */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
        </Button>

        {/* Theme toggle button */}
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* User menu */}
        <div className="flex items-center gap-3 pl-4 border-l">
          <Avatar fallback="JD" />
          <div className="hidden md:block">
            <p className="text-sm font-medium text-gray-900">John Doe</p>
            <p className="text-xs text-gray-500">Admin</p>
          </div>
          <Button variant="ghost" size="icon">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
