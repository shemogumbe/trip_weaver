# TripWeaver Frontend

A modern, elegant React TypeScript frontend for AI-powered trip planning.

## Features

- **Elegant UI**: Simplistic user interface with Tailwind CSS
-  **Smart Search**: Comprehensive search form with validation
-  **Responsive Design**: Works perfectly on desktop, tablet, and mobile
-  **Context API**: Efficient state management with React Context
-  **PDF Export**: Export trip plans as professional PDF documents
-  **Real-time Updates**: Live loading states and error handling
-  **Modern Icons**: Beautiful Lucide React icons throughout

## Tech Stack

- **React 18** with TypeScript
- **Context API** for state management
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **React Hot Toast** for notifications
- **jsPDF** for PDF generation
- **Axios** for API calls

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm start
```

The app will open at http://localhost:3000

### 3. Build for Production
```bash
npm run build
```

## Project Structure

```
src/
├── components/          # React components
│   ├── SearchForm.tsx   # Main search interface
│   └── TripResults.tsx  # Results display
├── context/             # Context API
│   └── TripContext.tsx  # Global state management
├── reducers/            # State reducers
│   └── tripReducer.ts   # Trip state logic
├── types/               # TypeScript definitions
│   └── index.ts         # All type definitions
├── utils/               # Utility functions
│   └── pdfExport.ts     # PDF generation
├── App.tsx              # Main app component
├── index.tsx            # App entry point
└── index.css            # Global styles
```

## Key Components

### SearchForm
- Comprehensive trip planning form
- Real-time validation
- Hobby/interest selection
- Budget level picker
- Date range selection

### TripResults
- Clean results display
- Flight information with booking links
- Hotel recommendations with ratings
- Daily itinerary with activities
- PDF export functionality

### Context API
- Centralized state management
- Loading states
- Error handling
- Search history

## API Integration

The frontend connects to the backend API at `http://localhost:8000`:

- `POST /plan-trip` - Generate trip plan
- `GET /health` - Health check
- `GET /` - API information

## Features in Detail

### Search Interface
- **Origin/Destination**: Airport codes or city names
- **Date Selection**: Start and end dates with validation
- **Travelers**: Number of adults (1-8)
- **Budget Levels**: Low, Mid-range, Luxury with icons
- **Trip Types**: Vacation, Business, Honeymoon, etc.
- **Interests**: Pre-defined hobbies + custom additions

### Results Display
- **Flights**: Summary, times, stops, pricing, booking links
- **Hotels**: Name, location, ratings, amenities, pricing
- **Activities**: Daily itinerary with morning/afternoon/evening slots
- **Duration Indicators**: Color-coded activity durations
- **Processing Logs**: Show data refinement statistics

### PDF Export
- Professional PDF layout
- Complete trip summary
- All flights, hotels, and activities
- Branded header and footer
- Automatic filename generation

## Styling

- **Tailwind CSS**: Utility-first CSS framework
- **Responsive Design**: Mobile-first approach
- **Custom Animations**: Smooth transitions and loading states
- **Color Scheme**: Blue and purple gradient theme
- **Typography**: Clean, readable fonts

## Development

### Available Scripts
- `npm start` - Development server
- `npm build` - Production build
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

### Environment Variables
The app uses a proxy to connect to the backend API. Make sure the backend is running on port 8000.

### Code Quality
- TypeScript for type safety
- ESLint for code quality
- Prettier for code formatting
- Responsive design principles

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Lazy loading for components
- Optimized bundle size
- Efficient re-renders with Context API
- Smooth animations with CSS transitions

## Contributing

1. Follow TypeScript best practices
2. Use semantic HTML
3. Maintain responsive design
4. Add proper error handling
5. Include loading states
6. Test on multiple devices
