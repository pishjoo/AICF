'use client';

export function Header() {
  return (
    <header className="h-16 bg-white border-b flex items-center justify-between px-6">
      <div className="text-lg font-semibold">AICF v2 Dashboard</div>
      <div className="flex items-center space-x-4">
        <span className="text-sm text-gray-600">Welcome</span>
      </div>
    </header>
  );
}
