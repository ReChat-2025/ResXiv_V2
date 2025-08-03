import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import { AuthProvider } from "@/components/auth/auth-provider";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

const manrope = Manrope({ 
  subsets: ["latin"], 
  variable: "--font-manrope", 
  weight: ["400", "500", "600", "700"] 
});

export const metadata: Metadata = {
  title: "ResXiv",
  description: "Your research hub",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light">
      <body className={`${manrope.variable} font-sans antialiased`}>
        <AuthProvider>
          {children}
        </AuthProvider>
        <Toaster />
      </body>
    </html>
  );
}
