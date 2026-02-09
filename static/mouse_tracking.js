/**
 * Mouse Tracking Module
 * Tracks mouse position, quadrant entry/exit, and hover events on agent panels
 */

class MouseTracker {
    constructor() {
        this.tracking = {
            movements: [],
            quadrantEvents: [],
            agentHovers: [],
            startTime: Date.now()
        };

        this.currentQuadrant = null;
        this.quadrantStartTime = null;
        this.sampleInterval = 200; // Sample every 200ms
        this.lastSampleTime = 0;
        this.savedManually = false; // Track if data was manually saved

        // Store references to layout columns for accurate boundary detection
        this.leftColumn = null;
        this.rightColumn = null;

        // Track active hover sessions (element type -> start time)
        this.activeHovers = new Map();

        console.log('[Mouse Tracking] MouseTracker instance created at', new Date(this.tracking.startTime).toISOString());

        this.init();
    }

    init() {
        console.log('[Mouse Tracking] Initializing mouse tracker');

        // Cache column elements for accurate boundary detection
        this.leftColumn = document.querySelector('.sidebar-user');
        this.rightColumn = document.querySelector('.sidebar-profile');

        if (this.leftColumn && this.rightColumn) {
            console.log('[Mouse Tracking] Layout columns found - using actual DOM boundaries');
        } else {
            console.warn('[Mouse Tracking] Could not find layout columns - falling back to percentage-based detection');
        }

        // Track mouse movement
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));

        // Track agent panel hovers
        this.setupAgentHoverTracking();

        // Save data when leaving page (only if not already saved manually)
        window.addEventListener('beforeunload', () => {
            if (!this.savedManually) {
                console.log('[Mouse Tracking] beforeunload - saving data');
                // Use sendBeacon as fallback for beforeunload (synchronous)
                const data = this.getTrackingData();
                const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
                const sessionId = window.location.pathname.split('/')[2];
                navigator.sendBeacon(`/store-mouse-tracking/${sessionId}/`, blob);
            } else {
                console.log('[Mouse Tracking] beforeunload - skipping (already saved manually)');
            }
        });

        console.log('[Mouse Tracking] Mouse tracker initialized successfully');
    }

    handleMouseMove(event) {
        const now = Date.now();

        // Sample at interval to avoid too much data
        if (now - this.lastSampleTime < this.sampleInterval) {
            return;
        }

        this.lastSampleTime = now;

        const x = event.clientX;
        const y = event.clientY;
        const timestamp = now - this.tracking.startTime;

        // Record position
        this.tracking.movements.push({
            x: x,
            y: y,
            timestamp: timestamp
        });

        // Log every 50 movements for debugging
        if (this.tracking.movements.length % 50 === 0) {
            console.log(`[Mouse Tracking] Captured ${this.tracking.movements.length} mouse movements`);
        }

        // Detect quadrant
        const quadrant = this.detectQuadrant(x, y);

        // Track quadrant changes
        if (quadrant !== this.currentQuadrant) {
            if (this.currentQuadrant !== null) {
                // Record complete quadrant visit with all timestamps
                const exitTimestamp = timestamp;
                const entryTimestamp = this.quadrantStartTime;
                const duration = exitTimestamp - entryTimestamp;

                this.tracking.quadrantEvents.push({
                    quadrant: this.currentQuadrant,
                    entry_timestamp_ms: entryTimestamp,
                    exit_timestamp_ms: exitTimestamp,
                    duration_ms: duration,
                    entry_timestamp_iso: new Date(this.tracking.startTime + entryTimestamp).toISOString(),
                    exit_timestamp_iso: new Date(this.tracking.startTime + exitTimestamp).toISOString()
                });
                console.log(`[Mouse Tracking] Completed visit to ${this.currentQuadrant}, duration: ${duration}ms`);
            }

            // Start tracking new quadrant
            this.currentQuadrant = quadrant;
            this.quadrantStartTime = timestamp;
            console.log(`[Mouse Tracking] Entered ${quadrant}`);
        }
    }

    detectQuadrant(x, y) {
        // Use actual DOM element boundaries if available
        if (this.leftColumn && this.rightColumn) {
            const leftRect = this.leftColumn.getBoundingClientRect();
            const rightRect = this.rightColumn.getBoundingClientRect();

            // Left sidebar: from start to right edge of left column
            if (x <= leftRect.right) {
                return 'left_sidebar';
            }
            // Right agents: from left edge of right column to end
            else if (x >= rightRect.left) {
                return 'right_agents';
            }
            // Center chat: everything between left and right columns
            else {
                return 'center_chat';
            }
        } else {
            // Fallback to percentage-based detection if columns not found
            const windowWidth = window.innerWidth;
            if (x < windowWidth * 0.25) {
                return 'left_sidebar';
            } else if (x < windowWidth * 0.75) {
                return 'center_chat';
            } else {
                return 'right_agents';
            }
        }
    }

    setupAgentHoverTracking() {
        const troubleWindow = document.getElementById('troubleWindow');

        if (troubleWindow) {
            console.log('[Mouse Tracking] Setting up tracking for info_agent');
            this.trackElementHover(troubleWindow, 'info_agent');
        } else {
            console.log('[Mouse Tracking] troubleWindow (info_agent) not found');
        }

        // Use MutationObserver to track dynamically added emo agent cards
        const supportWindow = document.getElementById('supportWindow');
        if (supportWindow) {
            console.log('[Mouse Tracking] Setting up tracking for emo_agent components');

            // Track existing cards
            this.setupEmoAgentTracking();

            // Watch for new cards being added
            const observer = new MutationObserver(() => {
                this.setupEmoAgentTracking();
            });

            observer.observe(supportWindow, {
                childList: true,
                subtree: true
            });
        } else {
            console.log('[Mouse Tracking] supportWindow not found');
        }
    }

    setupEmoAgentTracking() {
        // Track sentiment card specifically
        const sentimentCard = document.querySelector('.emo-sentiment-card');
        if (sentimentCard && !sentimentCard.dataset.tracked) {
            sentimentCard.dataset.tracked = 'true';
            console.log('[Mouse Tracking] Setting up tracking for emo_sentiment');
            this.trackElementHover(sentimentCard, 'emo_sentiment');
        }

        // Track reframe card specifically
        const reframeCard = document.querySelector('.emo-reframe-card');
        if (reframeCard && !reframeCard.dataset.tracked) {
            reframeCard.dataset.tracked = 'true';
            console.log('[Mouse Tracking] Setting up tracking for emo_reframe');
            this.trackElementHover(reframeCard, 'emo_reframe');
        }
    }

    trackElementHover(element, agentType) {
        element.addEventListener('mouseenter', () => {
            const entryTime = Date.now() - this.tracking.startTime;
            this.activeHovers.set(agentType, entryTime);
            console.log(`[Mouse Tracking] Hover started on ${agentType}`);
        });

        element.addEventListener('mouseleave', () => {
            if (this.activeHovers.has(agentType)) {
                const entryTime = this.activeHovers.get(agentType);
                const exitTime = Date.now() - this.tracking.startTime;
                const duration = exitTime - entryTime;

                // Record one complete hover event with all timestamps
                this.tracking.agentHovers.push({
                    agent: agentType,
                    entry_timestamp_ms: entryTime,
                    exit_timestamp_ms: exitTime,
                    duration_ms: duration,
                    entry_timestamp_iso: new Date(this.tracking.startTime + entryTime).toISOString(),
                    exit_timestamp_iso: new Date(this.tracking.startTime + exitTime).toISOString()
                });

                console.log(`[Mouse Tracking] Hover completed on ${agentType}, duration: ${duration}ms`);
                this.activeHovers.delete(agentType);
            }
        });
    }

    getTrackingData() {
        const now = Date.now();
        const currentTimestamp = now - this.tracking.startTime;

        // Finalize any active quadrant visit
        if (this.currentQuadrant !== null && this.quadrantStartTime !== null) {
            const duration = currentTimestamp - this.quadrantStartTime;
            this.tracking.quadrantEvents.push({
                quadrant: this.currentQuadrant,
                entry_timestamp_ms: this.quadrantStartTime,
                exit_timestamp_ms: currentTimestamp,
                duration_ms: duration,
                entry_timestamp_iso: new Date(this.tracking.startTime + this.quadrantStartTime).toISOString(),
                exit_timestamp_iso: new Date(now).toISOString()
            });
            console.log(`[Mouse Tracking] Finalizing active quadrant visit: ${this.currentQuadrant}, duration: ${duration}ms`);
            this.currentQuadrant = null;
            this.quadrantStartTime = null;
        }

        // Finalize any active agent hovers
        if (this.activeHovers.size > 0) {
            this.activeHovers.forEach((entryTime, agentType) => {
                const duration = currentTimestamp - entryTime;
                this.tracking.agentHovers.push({
                    agent: agentType,
                    entry_timestamp_ms: entryTime,
                    exit_timestamp_ms: currentTimestamp,
                    duration_ms: duration,
                    entry_timestamp_iso: new Date(this.tracking.startTime + entryTime).toISOString(),
                    exit_timestamp_iso: new Date(now).toISOString()
                });
                console.log(`[Mouse Tracking] Finalizing active hover: ${agentType}, duration: ${duration}ms`);
            });
            this.activeHovers.clear();
        }

        return {
            ...this.tracking,
            totalDuration: currentTimestamp
        };
    }

    saveTrackingData() {
        const sessionId = window.location.pathname.split('/')[2];
        const data = this.getTrackingData();

        console.log('[Mouse Tracking] Saving tracking data:', {
            movements: data.movements.length,
            quadrantEvents: data.quadrantEvents.length,
            agentHovers: data.agentHovers.length,
            totalDuration: data.totalDuration,
            startTime: new Date(data.startTime).toISOString()
        });
        console.log('[Mouse Tracking] Sample movement data:', data.movements.slice(0, 3));
        console.log('[Mouse Tracking] Sample quadrant data:', data.quadrantEvents.slice(0, 3));

        // Use fetch instead of sendBeacon for better compatibility with Flask
        return fetch(`/store-mouse-tracking/${sessionId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
            keepalive: true  // Ensures request completes even if page is closing
        })
        .then(response => response.json())
        .then(result => {
            this.savedManually = true; // Mark as saved to prevent duplicate beforeunload save
            console.log('[Mouse Tracking] Data saved successfully:', result);
            return result;
        })
        .catch(error => {
            console.error('[Mouse Tracking] Error saving data:', error);
            throw error;
        });
    }

    reset() {
        // Reset tracking for new round
        console.log('[Mouse Tracking] Resetting tracker for new round');
        this.tracking = {
            movements: [],
            quadrantEvents: [],
            agentHovers: [],
            startTime: Date.now()
        };
        this.currentQuadrant = null;
        this.quadrantStartTime = null;
        this.activeHovers.clear(); // Clear active hover sessions
        this.savedManually = false; // Reset save flag
        console.log('[Mouse Tracking] Tracker reset complete at', new Date(this.tracking.startTime).toISOString());
    }
}

// Initialize tracker when page loads
let mouseTracker = null;

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on chat pages, NOT on survey/landing/complete pages
    const path = window.location.pathname;
    const isChatPage = path.includes('/index/');

    if (isChatPage) {
        mouseTracker = new MouseTracker();
        console.log('[Mouse Tracking] Tracker initialized on chat page');
    } else {
        console.log('[Mouse Tracking] Skipping tracker initialization - not a chat page (path:', path, ')');
    }
});

// Expose function to manually save tracking data (e.g., at round completion)
function saveMouseTracking() {
    if (mouseTracker) {
        console.log('[Mouse Tracking] saveMouseTracking() called - saving data');
        return mouseTracker.saveTrackingData();
    }
    console.log('[Mouse Tracking] saveMouseTracking() called but mouseTracker is null (likely on survey page - skipping)');
    return Promise.resolve();
}

// Expose function to reset tracking (e.g., starting new round)
function resetMouseTracking() {
    if (mouseTracker) {
        mouseTracker.reset();
    }
}
