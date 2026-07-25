'use client';

export function Sidebar() {
  return (
    <aside className="w-64 h-screen bg-gray-900 text-white p-4">
      <div className="text-xl font-bold mb-8">AICF v2</div>
      <nav>
        <ul className="space-y-2">
          <li>
            <a href="#" className="block py-2 px-4 rounded hover:bg-gray-800">
              Dashboard
            </a>
          </li>
          <li>
            <a href="#" className="block py-2 px-4 rounded hover:bg-gray-800">
              Settings
            </a>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
