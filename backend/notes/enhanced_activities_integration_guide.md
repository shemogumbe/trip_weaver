# Enhanced Activities Integration Guide

## Overview

This guide shows how to integrate the enhanced activities agent that provides:

- **2-3x more diverse activities** with geographic refinement
- **Better hobby-specific coverage** using targeted searches
- **Hybrid search approach** (Tavily + web search for broader coverage)
- **Controlled latency** (15-30 seconds vs 5-8 seconds original)

## Current vs Enhanced Approach

### Current Approach (optimized_activities_agent_with_openai)
- ✅ **Fast**: 5-8 seconds
- ✅ **Cost efficient**: 1 Tavily call + 1 OpenAI call
- ❌ **Limited diversity**: Single generic prompt for all hobbies
- ❌ **No geographic refinement**: Activities not distributed across city areas
- ❌ **Generic results**: Often produces similar activities regardless of hobbies

### Enhanced Approach (practical_enhanced_activities_agent)
- ✅ **Rich diversity**: 2-3x more activities with better coverage
- ✅ **Hobby-specific**: Separate generation for each hobby with geographic refinement  
- ✅ **Real location data**: Uses search results to get actual place names and addresses
- ✅ **Geographic spread**: Central, downtown, suburbs, nearby areas
- ⚠️ **Slower**: 15-30 seconds (still acceptable for trip planning)
- ⚠️ **More API calls**: ~2-4 calls per hobby (controlled to prevent excessive usage)

## Quick Integration Steps

### 1. Install Dependencies
```bash
pip install beautifulsoup4 lxml
```

### 2. Test the Enhanced Approach
```bash
python test_enhanced_activities.py
```

This will compare both approaches and show you:
- Processing time difference
- Activity count improvement
- Sample activities from each approach
- Recommendations based on your results

### 3. Switch to Enhanced Agent (if satisfied with test results)

Update `app/graph/build_graph.py`:

```python
# BEFORE:
from app.graph.agents import destination_research, flight_agent, stay_agent, budget_agent, itinerary_synthesizer, optimized_activities_agent_with_openai

def build_graph():
    g = StateGraph(RunState)
    # ...
    g.add_node("activities_agent", optimized_activities_agent_with_openai)
    # ...
```

```python
# AFTER:
from app.graph.agents import destination_research, flight_agent, stay_agent, budget_agent, itinerary_synthesizer
from app.graph.practical_enhanced_activities import practical_enhanced_activities_agent

def build_graph():
    g = StateGraph(RunState)
    # ...  
    g.add_node("activities_agent", practical_enhanced_activities_agent)
    # ...
```

### 4. Rollback Strategy (if needed)

If the enhanced approach doesn't work well, simply revert the change in `build_graph.py`:

```python
# Rollback to original
from app.graph.agents import optimized_activities_agent_with_openai
g.add_node("activities_agent", optimized_activities_agent_with_openai)
```

## Configuration Options

### Adjust Activity Quantity

In `practical_enhanced_activities.py`, modify the multiplier:

```python
# Current: generates ~2.5x base activities
hobby_multiplier = min(2.5, 1.2 + (len(p.hobbies) * 0.3))

# Conservative: ~1.5x base activities (faster)
hobby_multiplier = min(1.8, 1.0 + (len(p.hobbies) * 0.2))

# Aggressive: ~3x base activities (more diverse, slower)  
hobby_multiplier = min(3.0, 1.5 + (len(p.hobbies) * 0.4))
```

### Control Search Depth

Adjust geographic areas per hobby:

```python
# Current: 2 areas per hobby
for area in geo_areas[:2]:

# Conservative: 1 area per hobby (faster)
for area in geo_areas[:1]:

# Aggressive: 3 areas per hobby (more comprehensive)
for area in geo_areas[:3]:
```

## Monitoring and Debugging

### Activity Generation Logs

The enhanced agent logs detailed information:

```python
# Check logs after trip generation
for log in result["logs"]:
    if log.get("stage") == "Enhanced Activities":
        print(f"Generated {log['total_activities']} activities")
        print(f"Processed {log['hobbies_processed']} hobbies")
```

### Common Issues and Solutions

**Issue: Enhanced agent taking too long (>45 seconds)**
- Reduce `hobby_multiplier` to 1.8
- Limit geographic areas to 1 per hobby
- Check network connectivity

**Issue: Not enough activities generated**
- Increase `activities_per_hobby` in `generate_hobby_activities_enhanced`
- Add more fallback general activities

**Issue: Activities not diverse enough**
- Check if hobbies are being recognized properly
- Verify search results are returning relevant data
- Increase geographic area coverage

## Hybrid Approach (Recommended for Production)

For production, you might want a hybrid approach that falls back:

```python
def hybrid_activities_agent(state: RunState) -> RunState:
    """Hybrid approach: try enhanced, fallback to original if needed"""
    
    try:
        # Try enhanced approach with timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Enhanced activities timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(45)  # 45 second timeout
        
        result = practical_enhanced_activities_agent(state)
        signal.alarm(0)  # Cancel timeout
        
        # Check if we got enough activities
        if len(result.plan.activities_catalog) >= (len(state.prefs.hobbies) * 2):
            return result
        else:
            raise ValueError("Insufficient activities generated")
            
    except (TimeoutError, Exception) as e:
        logger.warning(f"Enhanced approach failed ({e}), using original")
        signal.alarm(0)  # Cancel any pending timeout
        return optimized_activities_agent_with_openai(state)
```

## Expected Results

After implementing the enhanced approach, you should see:

### Dubai Example (4 hobbies: fine dining, nightlife, golf, shopping)
- **Original**: ~9 activities, mostly generic
- **Enhanced**: ~18-24 activities with specific venues
- **Examples**:
  - "Dinner at Nobu Dubai" vs "Fine dining experience"
  - "Golf at Emirates Golf Club" vs "Golf course visit"  
  - "Shopping at Gold Souk" vs "Shopping mall visit"

### Lagos Example (3 hobbies: beach, culture, nightlife)
- **Original**: ~6 activities
- **Enhanced**: ~12-18 activities across different areas
- **Geographic spread**: Victoria Island, Lagos Island, Mainland areas

## Support and Troubleshooting

If you encounter issues:

1. **Run the test script first**: `python test_enhanced_activities.py`
2. **Check logs**: Enhanced agent provides detailed logging
3. **Verify dependencies**: Ensure `beautifulsoup4` and `lxml` are installed
4. **API limits**: Monitor Tavily API usage (enhanced approach uses more calls)
5. **Fallback option**: Keep original agent available for rollback

The enhanced approach is designed to be a drop-in replacement that provides significantly better activity coverage while maintaining reasonable performance for trip planning use cases.