import React from 'react';
import Image from 'next/image';
import { cn } from '@/lib/utils';

interface ResXivLogoProps {
  width?: number;
  height?: number;
  className?: string;
}

export function ResXivLogo({ 
  width = 120, 
  height = 37, 
  className 
}: ResXivLogoProps) {
  return (
    <Image
      src="/ResXiv_logo_navbar.svg"
      alt="ResXiv Logo"
      width={width}
      height={height}
      className={cn("object-contain", className)}
      priority
    />
  );
}

export default ResXivLogo; 