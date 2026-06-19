import { Link } from 'react-router-dom';
import { Home, AlertCircle } from 'lucide-react';
import Button from '@/components/common/Button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-24 h-24 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center">
            <AlertCircle size={48} className="text-gray-600" />
          </div>
        </div>

        {/* Error code */}
        <h1 className="text-8xl font-black text-gray-800 mb-2">404</h1>

        {/* Message */}
        <h2 className="text-xl font-semibold text-gray-300 mb-2">
          Trang không tồn tại
        </h2>
        <p className="text-sm text-gray-500 mb-8">
          Trang bạn đang tìm kiếm không tồn tại hoặc đã bị di chuyển.
        </p>

        {/* Action */}
        <Link to="/">
          <Button variant="primary" leftIcon={<Home size={16} />}>
            Về trang chủ
          </Button>
        </Link>
      </div>
    </div>
  );
}
