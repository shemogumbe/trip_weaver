import React from 'react';
import { Plane, Hotel, MapPin, Clock, DollarSign, Star, Download, ExternalLink, Calendar } from 'lucide-react';
import { TripPlan, Flight, Stay, DayPlan, Activity } from '../types';
import { useTrip } from '../context/TripContext';
import { exportToPDF } from '../utils/pdfExport';

interface TripResultsProps {
  plan: TripPlan;
}

export const TripResults: React.FC<TripResultsProps> = ({ plan }) => {
  const { state } = useTrip();

  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return 'Price not available';
    return `${currency || 'USD'} ${price.toLocaleString()}`;
  };

  const formatDuration = (hours?: number) => {
    if (!hours) return 'Duration not specified';
    if (hours < 1) return `${Math.round(hours * 60)} minutes`;
    if (hours === 1) return '1 hour';
    return `${hours} hours`;
  };

  const getDurationColor = (hours?: number) => {
    if (!hours) return 'text-gray-500';
    if (hours <= 4) return 'text-green-600';
    if (hours <= 8) return 'text-yellow-600';
    return 'text-red-600';
  };

  const handleExportPDF = () => {
    exportToPDF(plan, state.lastSearch);
  };

  return (
    <div className="space-y-8">
      {/* Header with Export Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Your Trip Plan</h2>
          <p className="text-gray-600">
            {state.lastSearch && (
              <>
                {state.lastSearch.origin} → {state.lastSearch.destination} • {' '}
                {new Date(state.lastSearch.start_date).toLocaleDateString()} - {' '}
                {new Date(state.lastSearch.end_date).toLocaleDateString()}
              </>
            )}
          </p>
        </div>
        <button
          onClick={handleExportPDF}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export PDF
        </button>
      </div>

      {/* Flights Section */}
      {plan.flights.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-blue-100 rounded-xl">
              <Plane className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Flights</h3>
          </div>
          <div className="grid gap-4">
            {plan.flights.map((flight: Flight, index: number) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900">{flight.summary}</h4>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                      {flight.depart_time && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          Depart: {flight.depart_time}
                        </span>
                      )}
                      {flight.arrive_time && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          Arrive: {flight.arrive_time}
                        </span>
                      )}
                      {flight.stops !== undefined && (
                        <span className="flex items-center gap-1">
                          <Plane className="w-4 h-4" />
                          {flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-gray-900">
                      {formatPrice(flight.est_price, flight.currency)}
                    </div>
                    {flight.booking_links && flight.booking_links.length > 0 && (
                      <a
                        href={flight.booking_links[0]}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 mt-1"
                      >
                        Book Now <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stays Section */}
      {plan.stays.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-green-100 rounded-xl">
              <Hotel className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Accommodations</h3>
          </div>
          <div className="grid gap-4">
            {plan.stays.map((stay: Stay, index: number) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900">{stay.name}</h4>
                    <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
                      <MapPin className="w-4 h-4" />
                      {stay.area}
                    </div>
                    {stay.score && (
                      <div className="flex items-center gap-1 mt-2">
                        <Star className="w-4 h-4 text-yellow-500 fill-current" />
                        <span className="text-sm font-medium text-gray-700">{stay.score}/10</span>
                      </div>
                    )}
                    {stay.highlights && stay.highlights.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {stay.highlights.map((highlight, idx) => (
                          <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                            {highlight}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-gray-900">
                      {formatPrice(stay.est_price_per_night, stay.currency)}/night
                    </div>
                    {stay.booking_links && stay.booking_links.length > 0 && (
                      <a
                        href={stay.booking_links[0]}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 mt-1"
                      >
                        Book Now <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activities Section */}
      {plan.activities.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-purple-100 rounded-xl">
              <Calendar className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Daily Itinerary</h3>
          </div>
          <div className="space-y-6">
            {plan.activities.map((day: DayPlan, dayIndex: number) => (
              <div key={dayIndex} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-4">
                  <Calendar className="w-5 h-5 text-gray-600" />
                  <h4 className="font-semibold text-gray-900">
                    Day {dayIndex + 1} - {new Date(day.date).toLocaleDateString('en-US', { 
                      weekday: 'long', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </h4>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {['morning', 'afternoon', 'evening'].map((timeSlot) => {
                    const activity = day[timeSlot as keyof DayPlan] as Activity;
                    return (
                      <div key={timeSlot} className="space-y-2">
                        <h5 className="text-sm font-medium text-gray-700 capitalize">{timeSlot}</h5>
                        {activity ? (
                          <div className="bg-gray-50 rounded-lg p-3">
                            <h6 className="font-medium text-gray-900">{activity.title}</h6>
                            <div className="flex items-center gap-1 mt-1 text-sm text-gray-600">
                              <MapPin className="w-3 h-3" />
                              {activity.location}
                            </div>
                            <div className="flex items-center justify-between mt-2">
                              <span className={`text-sm font-medium ${getDurationColor(activity.duration_hours)}`}>
                                {formatDuration(activity.duration_hours)}
                              </span>
                              {activity.est_price && (
                                <span className="text-sm font-medium text-gray-700">
                                  {formatPrice(activity.est_price, activity.currency)}
                                </span>
                              )}
                            </div>
                            {activity.tags && activity.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {activity.tags.map((tag, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="bg-gray-50 rounded-lg p-3 text-center text-gray-500 text-sm">
                            Free time
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Logs */}
      {/* {state.logs.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Summary</h3>
          <div className="space-y-2">
            {state.logs.map((log, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-700">{log.stage}</span>
                <span className="text-gray-600">
                  {log.raw_count} raw → {log.refined_count} refined
                  {log.error && <span className="text-red-600 ml-2">({log.error})</span>}
                </span>
              </div>
            ))}
          </div>
        </div>
      )} */}
    </div>
  );
};
