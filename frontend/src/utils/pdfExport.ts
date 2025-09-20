import { jsPDF } from "jspdf";

import { TripPlan, TripRequest } from '../types';

export const exportToPDF = (plan: TripPlan, lastSearch: TripRequest | null) => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  let yPosition = 20;

  // Helper function to add text with word wrapping
  const addText = (text: string, x: number, y: number, maxWidth: number, fontSize: number = 12) => {
    doc.setFontSize(fontSize);
    const lines = doc.splitTextToSize(text, maxWidth);
    doc.text(lines, x, y);
    return y + (lines.length * fontSize * 0.4);
  };

  // Helper function to check if we need a new page
  const checkNewPage = (requiredSpace: number) => {
    if (yPosition + requiredSpace > pageHeight - 20) {
      doc.addPage();
      yPosition = 20;
      return true;
    }
    return false;
  };

  // Header
  doc.setFillColor(59, 130, 246); // Blue background
  doc.rect(0, 0, pageWidth, 30, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(20);
  doc.setFont('helvetica', 'bold');
  doc.text('TripWeaver - Your Travel Plan', 20, 20);

  yPosition = 40;

  // Trip Summary
  if (lastSearch) {
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Trip Summary', 20, yPosition);
    yPosition += 15;

    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    yPosition = addText(`From: ${lastSearch.origin}`, 20, yPosition, pageWidth - 40);
    yPosition = addText(`To: ${lastSearch.destination}`, 20, yPosition, pageWidth - 40);
    yPosition = addText(`Dates: ${new Date(lastSearch.start_date).toLocaleDateString()} - ${new Date(lastSearch.end_date).toLocaleDateString()}`, 20, yPosition, pageWidth - 40);
    yPosition = addText(`Travelers: ${lastSearch.adults}`, 20, yPosition, pageWidth - 40);
    yPosition = addText(`Budget: ${lastSearch.budget_level}`, 20, yPosition, pageWidth - 40);
    yPosition = addText(`Trip Type: ${lastSearch.trip_type}`, 20, yPosition, pageWidth - 40);
    
    if (lastSearch.hobbies.length > 0) {
      yPosition = addText(`Interests: ${lastSearch.hobbies.join(', ')}`, 20, yPosition, pageWidth - 40);
    }
    
    yPosition += 10;
  }

  // Flights Section
  if (plan.flights.length > 0) {
    checkNewPage(30);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Flights', 20, yPosition);
    yPosition += 15;

    plan.flights.forEach((flight, index) => {
      checkNewPage(25);
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      yPosition = addText(`${index + 1}. ${flight.summary}`, 20, yPosition, pageWidth - 40);
      
      doc.setFont('helvetica', 'normal');
      if (flight.depart_time && flight.arrive_time) {
        yPosition = addText(`Departure: ${flight.depart_time} | Arrival: ${flight.arrive_time}`, 20, yPosition, pageWidth - 40);
      }
      if (flight.stops !== undefined) {
        yPosition = addText(`Stops: ${flight.stops === 0 ? 'Direct' : flight.stops}`, 20, yPosition, pageWidth - 40);
      }
      if (flight.est_price) {
        yPosition = addText(`Price: ${flight.currency || 'USD'} ${flight.est_price.toLocaleString()}`, 20, yPosition, pageWidth - 40);
      }
      yPosition += 5;
    });
    yPosition += 10;
  }

  // Stays Section
  if (plan.stays.length > 0) {
    checkNewPage(30);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Accommodations', 20, yPosition);
    yPosition += 15;

    plan.stays.forEach((stay, index) => {
      checkNewPage(30);
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      yPosition = addText(`${index + 1}. ${stay.name}`, 20, yPosition, pageWidth - 40);
      
      doc.setFont('helvetica', 'normal');
      yPosition = addText(`Location: ${stay.area}`, 20, yPosition, pageWidth - 40);
      if (stay.score) {
        yPosition = addText(`Rating: ${stay.score}/10`, 20, yPosition, pageWidth - 40);
      }
      if (stay.est_price_per_night) {
        yPosition = addText(`Price: ${stay.currency || 'USD'} ${stay.est_price_per_night.toLocaleString()}/night`, 20, yPosition, pageWidth - 40);
      }
      if (stay.highlights && stay.highlights.length > 0) {
        yPosition = addText(`Highlights: ${stay.highlights.join(', ')}`, 20, yPosition, pageWidth - 40);
      }
      yPosition += 5;
    });
    yPosition += 10;
  }

  // Activities Section
  if (plan.activities.length > 0) {
    checkNewPage(30);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Daily Itinerary', 20, yPosition);
    yPosition += 15;

    plan.activities.forEach((day, dayIndex) => {
      checkNewPage(40);
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      yPosition = addText(`Day ${dayIndex + 1} - ${new Date(day.date).toLocaleDateString()}`, 20, yPosition, pageWidth - 40);
      yPosition += 5;

      ['morning', 'afternoon', 'evening'].forEach((timeSlot) => {
        const activity = day[timeSlot as keyof typeof day];
        if (activity && typeof activity === 'object' && 'title' in activity) {
          checkNewPage(20);
          doc.setFontSize(12);
          doc.setFont('helvetica', 'bold');
          yPosition = addText(`${timeSlot.charAt(0).toUpperCase() + timeSlot.slice(1)}: ${activity.title}`, 30, yPosition, pageWidth - 50);
          
          doc.setFont('helvetica', 'normal');
          yPosition = addText(`Location: ${activity.location}`, 30, yPosition, pageWidth - 50);
          if (activity.duration_hours) {
            yPosition = addText(`Duration: ${activity.duration_hours} hours`, 30, yPosition, pageWidth - 50);
          }
          if (activity.est_price) {
            yPosition = addText(`Price: ${activity.currency || 'USD'} ${activity.est_price.toLocaleString()}`, 30, yPosition, pageWidth - 50);
          }
          if (activity.tags && activity.tags.length > 0) {
            yPosition = addText(`Tags: ${activity.tags.join(', ')}`, 30, yPosition, pageWidth - 50);
          }
          yPosition += 3;
        }
      });
      yPosition += 5;
    });
  }

  // Footer
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(10);
    doc.setTextColor(128, 128, 128);
    doc.text(`Generated by TripWeaver - Page ${i} of ${totalPages}`, pageWidth - 80, pageHeight - 10);
  }

  // Save the PDF
  const fileName = lastSearch 
    ? `TripWeaver_${lastSearch.origin}_to_${lastSearch.destination}_${new Date().toISOString().split('T')[0]}.pdf`
    : `TripWeaver_Plan_${new Date().toISOString().split('T')[0]}.pdf`;
  
  doc.save(fileName);
};
