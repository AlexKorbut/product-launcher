import type { Metadata } from 'next';
import './globals.css';
import Nav from './nav';

export const metadata: Metadata = {
  title: 'TG Channel Studio',
  description: 'Управление генерацией Telegram-каналов',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <div className="layout">
          <Nav />
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
