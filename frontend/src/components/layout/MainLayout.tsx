import { Outlet } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/common/Siderbar';
import Header from './Header';
import Footer from './Footer';
import { websocketService } from '@/services/websocketService';

interface MainLayoutProps {
  wsConnected?: boolean;
}

export default function MainLayout({ wsConnected = false }: MainLayoutProps) {
  const [isWsConnected, setIsWsConnected] = useState(wsConnected || websocketService.isConnected);

  useEffect(() => {
    return websocketService.onStateChange((state) => {
      setIsWsConnected(state.status === 'connected');
    });
  }, []);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header wsConnected={isWsConnected} />

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>

        <Footer />
      </div>
    </div>
  );
}
