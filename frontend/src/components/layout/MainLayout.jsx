import Sidebar from './Sidebar';

export default function MainLayout({ children }) {
  return (
    <div className="min-h-screen bg-surface-page flex">
      <Sidebar />
      <main id="main-content" className="ml-[240px] flex-1 overflow-y-auto scrollbar-thin">
        <div className="px-8 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}
