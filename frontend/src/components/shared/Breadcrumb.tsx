import { Link } from 'react-router-dom';

interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export default function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <div className="px-4 py-4">
      <div className="flex items-center gap-2">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            {item.path ? (
              <Link 
                to={item.path} 
                className="text-base font-medium text-[#61758a] no-underline hover:text-[#121417]"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-base font-medium text-[#121417]">
                {item.label}
              </span>
            )}
            {index < items.length - 1 && (
              <span className="text-base font-medium text-[#61758a]">/</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}