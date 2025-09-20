import React, { useState } from 'react';
import { Search, MapPin, Calendar, Users, DollarSign, Heart, Plus, X } from 'lucide-react';
import { TripRequest } from '../types';
import { useTrip } from '../context/TripContext';

const BUDGET_LEVELS = [
  { value: 'low', label: 'Budget', icon: '💰' },
  { value: 'mid', label: 'Mid-range', icon: '💎' },
  { value: 'high', label: 'Luxury', icon: '👑' },
];

const TRIP_TYPES = [
  'vacation', 'business', 'honeymoon', 'family', 'adventure', 'cultural', 'relaxation', 'custom'
];

const COMMON_HOBBIES = [
  'beach', 'mountain', 'city tour', 'night life', 'fine dining', 'shopping', 
  'culture', 'history', 'art', 'music', 'sports', 'adventure', 'wildlife', 
  'photography', 'golf', 'spa', 'hiking', 'diving', 'sailing'
];

export const SearchForm: React.FC = () => {
  const { state, searchTrip } = useTrip();
  const [formData, setFormData] = useState<TripRequest>({
    origin: '',
    destination: '',
    start_date: '',
    end_date: '',
    hobbies: [],
    adults: 2,
    budget_level: 'mid',
    trip_type: 'vacation',
    constraints: {},
  });

  const [customHobby, setCustomHobby] = useState('');

  const handleInputChange = (field: keyof TripRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addHobby = (hobby: string) => {
    if (hobby && !formData.hobbies.includes(hobby)) {
      setFormData(prev => ({
        ...prev,
        hobbies: [...prev.hobbies, hobby]
      }));
    }
  };

  const removeHobby = (hobby: string) => {
    setFormData(prev => ({
      ...prev,
      hobbies: prev.hobbies.filter(h => h !== hobby)
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.origin || !formData.destination || !formData.start_date || !formData.end_date) {
      return;
    }
    await searchTrip(formData);
  };

  const isFormValid = formData.origin && formData.destination && formData.start_date && formData.end_date;

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-blue-100 rounded-xl">
          <Search className="w-6 h-6 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plan Your Perfect Trip</h1>
          <p className="text-gray-600">Get personalized recommendations with AI-powered planning</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Origin and Destination */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <MapPin className="w-4 h-4" />
              From
            </label>
            <input
              type="text"
              placeholder="e.g., NBO, Nairobi, JFK"
              value={formData.origin}
              onChange={(e) => handleInputChange('origin', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <MapPin className="w-4 h-4" />
              To
            </label>
            <input
              type="text"
              placeholder="e.g., Dubai, DXB, Paris"
              value={formData.destination}
              onChange={(e) => handleInputChange('destination', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Dates and Travelers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Calendar className="w-4 h-4" />
              Start Date
            </label>
            <input
              type="date"
              value={formData.start_date}
              onChange={(e) => handleInputChange('start_date', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Calendar className="w-4 h-4" />
              End Date
            </label>
            <input
              type="date"
              value={formData.end_date}
              onChange={(e) => handleInputChange('end_date', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Users className="w-4 h-4" />
              Travelers
            </label>
            <select
              value={formData.adults}
              onChange={(e) => handleInputChange('adults', parseInt(e.target.value))}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                <option key={num} value={num}>{num} {num === 1 ? 'Person' : 'People'}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Budget Level */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <DollarSign className="w-4 h-4" />
            Budget Level
          </label>
          <div className="grid grid-cols-3 gap-3">
            {BUDGET_LEVELS.map(level => (
              <button
                key={level.value}
                type="button"
                onClick={() => handleInputChange('budget_level', level.value)}
                className={`p-4 rounded-xl border-2 transition-all ${
                  formData.budget_level === level.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-2xl mb-1">{level.icon}</div>
                <div className="text-sm font-medium">{level.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Trip Type */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Heart className="w-4 h-4" />
            Trip Type
          </label>
          <select
            value={formData.trip_type}
            onChange={(e) => handleInputChange('trip_type', e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          >
            {TRIP_TYPES.map(type => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Hobbies/Interests */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-gray-700">Interests & Activities</label>
          
          {/* Selected Hobbies */}
          {formData.hobbies.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.hobbies.map(hobby => (
                <span
                  key={hobby}
                  className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {hobby}
                  <button
                    type="button"
                    onClick={() => removeHobby(hobby)}
                    className="hover:bg-blue-200 rounded-full p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Common Hobbies */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {COMMON_HOBBIES.map(hobby => (
              <button
                key={hobby}
                type="button"
                onClick={() => addHobby(hobby)}
                disabled={formData.hobbies.includes(hobby)}
                className={`p-2 text-sm rounded-lg border transition-all ${
                  formData.hobbies.includes(hobby)
                    ? 'bg-blue-100 text-blue-800 border-blue-200'
                    : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
                }`}
              >
                {hobby}
              </button>
            ))}
          </div>

          {/* Custom Hobby Input */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add custom interest..."
              value={customHobby}
              onChange={(e) => setCustomHobby(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="button"
              onClick={() => {
                addHobby(customHobby);
                setCustomHobby('');
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!isFormValid || state.isLoading}
          className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]"
        >
          {state.isLoading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Planning Your Trip...
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <Search className="w-5 h-5" />
              Generate Trip Plan
            </div>
          )}
        </button>
      </form>
    </div>
  );
};
