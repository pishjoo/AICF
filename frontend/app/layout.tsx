import type { Metadata } from 'next';
import { QueryProvider } from '@/providers/QueryProvider';

export const metadata: Metadata = {
  title: 'AICF v2 - AI Content Factory',
  description: 'AI-powered content factory for automated content generation and workflow management',
  keywords: ['AI', 'Content', 'Factory', 'Workflow', 'Automation'],
  authors: [{ name: 'AICF Team' }],
  viewport: 'width=device-width, initial-scale=1',
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
