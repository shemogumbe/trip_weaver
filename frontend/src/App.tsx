import React from 'react';
import { Toaster } from 'react-hot-toast';
import { TripProvider } from './context/TripContext';
import { SearchForm } from './components/SearchForm';
import { TripResults } from './components/TripResults';
import { useTrip } from './context/TripContext';
import { AlertCircle, Loader2 } from 'lucide-react';

const AppContent: React.FC = () => {
  const { state } = useTrip();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            ✈️ TripWeaver
          </h1>
          <p className="text-xl text-gray-600">
            AI-Powered Travel Planning
          </p>
        </div>

        {/* Search Form */}
        <SearchForm />

        {/* Loading State */}
        {state.isLoading && (
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="flex items-center justify-center gap-3 mb-4">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
              <h2 className="text-xl font-semibold text-gray-900">Planning Your Trip</h2>
            </div>
            <p className="text-gray-600">
              Our AI is researching flights, hotels, and activities for your perfect trip...
            </p>
            <div className="mt-6 space-y-2">
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
                <span>Searching for flights</span>
              </div>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse" />
                <span>Finding accommodations</span>
              </div>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" />
                <span>Planning activities</span>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {state.error && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-xl">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Oops! Something went wrong</h2>
                <p className="text-gray-600">We encountered an error while planning your trip</p>
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Error Details:</p>
              <p className="text-red-700 mt-1">{state.error}</p>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              <p>Please try again or check your input. Common issues:</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Make sure your dates are valid and in the future</li>
                <li>Check that your origin and destination are spelled correctly</li>
                <li>Ensure your end date is after your start date</li>
                <li>Try refreshing the page if the issue persists</li>
              </ul>
            </div>
          </div>
        )}

        {/* Results */}
        {state.tripPlan && !state.isLoading && (
          <TripResults plan={state.tripPlan} />
        )}

        {/* Empty State */}
        {!state.tripPlan && !state.isLoading && !state.error && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-4xl">✈️</span>
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                Ready to Plan Your Adventure?
              </h2>
              <p className="text-gray-600 mb-6">
                Fill out the form above to get personalized recommendations for flights, 
                accommodations, and activities tailored to your interests and budget.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-500">
                <div className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full" />
                  <span>AI-Powered Search</span>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full" />
                  <span>Real-time Pricing</span>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-purple-500 rounded-full" />
                  <span>PDF Export</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  );
};

const App: React.FC = () => {
  return (
    <TripProvider>
      <AppContent />
    </TripProvider>
  );
};

export default App;
