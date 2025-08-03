"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { appConfig } from "@/lib/config/app-config";

interface CalendarWidgetProps {
  currentMonth?: number;
  currentYear?: number;
  onDateSelect?: (date: Date) => void;
  className?: string;
  showNavigation?: boolean;
}

export function CalendarWidget({ 
  currentMonth = 5, // June (0-indexed) - configurable default
  currentYear = 2024,
  onDateSelect,
  className = "",
  showNavigation = true
}: CalendarWidgetProps) {
  const [month, setMonth] = useState(currentMonth);
  const [year, setYear] = useState(currentYear);

  // Get configuration values
  const config = appConfig;
  
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const dayNames = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

  const getDaysInMonth = (month: number, year: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (month: number, year: number) => {
    const day = new Date(year, month, 1).getDay();
    return day === 0 ? 6 : day - 1; // Convert Sunday (0) to be last (6)
  };

  const handlePreviousMonth = () => {
    if (month === 0) {
      setMonth(11);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 11) {
      setMonth(0);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  const handleDateClick = (day: number) => {
    const selectedDate = new Date(year, month, day);
    onDateSelect?.(selectedDate);
  };

  const isToday = (day: number) => {
    const today = new Date();
    return (
      today.getDate() === day &&
      today.getMonth() === month &&
      today.getFullYear() === year
    );
  };

  const renderCalendarDays = () => {
    const daysInMonth = getDaysInMonth(month, year);
    const firstDay = getFirstDayOfMonth(month, year);
    const days = [];

    // Previous month's trailing days
    const prevMonth = month === 0 ? 11 : month - 1;
    const prevYear = month === 0 ? year - 1 : year;
    const daysInPrevMonth = getDaysInMonth(prevMonth, prevYear);
    
    for (let i = firstDay - 1; i >= 0; i--) {
      days.push(
        <button
          key={`prev-${daysInPrevMonth - i}`}
          className="h-8 w-8 text-sm text-gray-500 hover:bg-accent rounded transition-colors"
          onClick={() => {
            setMonth(prevMonth);
            setYear(prevYear);
            handleDateClick(daysInPrevMonth - i);
          }}
        >
          {daysInPrevMonth - i}
        </button>
      );
    }

    // Current month's days
    for (let day = 1; day <= daysInMonth; day++) {
      const today = isToday(day);
      days.push(
        <button
          key={day}
          className={`h-8 w-8 text-sm rounded transition-colors ${
            today
              ? 'bg-primary text-primary-foreground font-semibold'
              : 'text-gray-700 hover:bg-accent'
          }`}
          onClick={() => handleDateClick(day)}
        >
          {day}
        </button>
      );
    }

    // Next month's leading days
    const remainingDays = 42 - days.length; // 6 rows × 7 days = 42 total cells
    const nextMonth = month === 11 ? 0 : month + 1;
    const nextYear = month === 11 ? year + 1 : year;
    
    for (let day = 1; day <= remainingDays; day++) {
      days.push(
        <button
          key={`next-${day}`}
          className="h-8 w-8 text-sm text-gray-500 hover:bg-accent rounded transition-colors"
          onClick={() => {
            setMonth(nextMonth);
            setYear(nextYear);
            handleDateClick(day);
          }}
        >
          {day}
        </button>
      );
    }

    return days;
  };

  return (
    <div className={`bg-card ${className}`}>
      {/* Calendar Header */}
      {showNavigation && (
        <div className="flex items-center justify-between mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={handlePreviousMonth}
            className="h-8 w-8 p-0 hover:bg-accent"
          >
            <Icon name="CaretLeft" size={16} weight="regular" />
          </Button>
          
          <h3 className="font-medium text-gray-800">
            {monthNames[month]} {year}
          </h3>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNextMonth}
            className="h-8 w-8 p-0 hover:bg-accent"
          >
            <Icon name="CaretRight" size={16} weight="regular" />
          </Button>
        </div>
      )}

      {/* Day Headers */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {dayNames.map((day) => (
          <div
            key={day}
            className="h-8 flex items-center justify-center text-xs font-medium text-gray-600"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {renderCalendarDays()}
      </div>
    </div>
  );
} 