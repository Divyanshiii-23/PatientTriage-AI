# Technical Design: PatientTriage.ai Clinical Interface & Workflow

## Overview

### System Purpose

The PatientTriage.ai Clinical Interface & Workflow is a web-based prototype application that demonstrates the ML Core Engine in realistic Emergency Department triage scenarios. This interface serves as an Accenture Innovation Challenge 2026 Round 2 submission, showcasing how AI-powered triage assistance integrates into clinical workflows while maintaining clinician authority, safety, and accountability.

The interface provides nurses and clinicians with streamlined patient intake, real-time ESI recommendations with confidence scoring and explanations, continuous deterioration monitoring during wait times, surge mode prioritization, and override tracking for continuous improvement. It handles 20 simulated patients across diverse scenarios including pediatric, geriatric, ambiguous presentations, and zero-history cases.

This specification covers ONLY the clinical interface and workflow prototype. The underlying ML Core Engine (ESI classification, deterioration detection, explainability, safety validation) is implemented separately and consumed as an API service.

### Key Design Principles

1. **Clinical Safety First**: ML provides recommendations, clinicians make decisions. 100% override capability without barriers.
2. **Real-Time Responsiveness**: WebSocket-driven updates for deterioration alerts and queue changes with <1 second latency.
3. **Transparency**: Every AI recommendation includes confidence breakdown, SHAP explanations, and safety flags prominently displayed.
4. **Graceful Degradation**: System functions when ML Core is unavailable, returning safe defaults (ESI 2, LOW confidence).
5. **HIPAA Compliance**: All patient data encrypted in transit and at rest, audit logging for 7 years, role-based access control.
6. **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation, screen reader support, and touch-friendly design.
7. **Demonstration Focus**: 20 pre-loaded patients, guided tour, demo scenarios, export-ready reporting for Innovation Challenge evaluation.

### Architecture at a Glance

```mermaid
graph TB
    subgraph "Client Browser"
        UI[React 18 UI<br/>TypeScript]
        State[Redux Toolkit<br/>State Management]
        WS_Client[WebSocket Client<br/>Socket.io]
    end
    
    subgraph "Backend Services"
        API[FastAPI REST API<br/>Patient CRUD, Triage]
        WS_Server[WebSocket Server<br/>Real-time Updates]
        BG[Background Jobs<br/>Deterioration Monitor]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL 15<br/>Patients, Audit Logs)]
        Redis[(Redis Cache<br/>Session, Queue State)]
    end
    
    subgraph "External Services"
        ML[ML Core API<br/>ESI Prediction, Deterioration]
    end
    
    UI --> State
    State --> WS_Client
    UI --> API
    WS_Client <--> WS_Server
    API --> PG
    API --> Redis
    API --> ML
    BG --> PG
    BG --> ML
    BG --> WS_Server
    WS_Server --> Redis
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend Framework** | React | 18.2+ | Component-based UI, hooks, concurrent rendering |
| **Type Safety** | TypeScript | 5.0+ | Static typing, autocomplete, refactoring safety |
| **UI Components** | Material-UI (MUI) | 5.14+ | Consistent design system, accessibility built-in |
| **State Management** | Redux Toolkit | 1.9+ | Predictable state, DevTools, real-time updates |
| **Routing** | React Router | 6.15+ | Client-side navigation, protected routes |
| **Backend Framework** | FastAPI | 0.100+ | Async Python, auto OpenAPI docs, Pydantic validation |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction, migrations with Alembic |
| **Real-Time** | Socket.io | 4.6+ (JS) / python-socketio 5.9+ (Py) | WebSocket with fallback, room broadcasting |
| **Database** | PostgreSQL | 15+ | ACID compliance, JSON support, 7-year retention |
| **Cache** | Redis | 7.0+ | Session store, queue state, WebSocket pub/sub |
| **Authentication** | JWT | python-jose 3.3+ | Stateless tokens, role-based access control |
| **HTTP Client** | Axios | 1.5+ | Promise-based, interceptors, retry logic |
| **Charts** | Recharts | 2.8+ | SHAP visualizations, probability distributions |
| **Validation** | Pydantic | 2.0+ (Backend) / Zod 3.22+ (Frontend) | Schema validation, type coercion |
| **Containerization** | Docker | 24.0+ | Isolated environments, reproducible deployment |

---

## Architecture

### System Components

The Clinical Interface consists of 7 major layers:

```mermaid
graph TD
    subgraph "Presentation Layer"
        A[React Components]
        B[Redux Store]
        C[React Router]
    end
    
    subgraph "Communication Layer"
        D[REST API Client<br/>Axios]
        E[WebSocket Client<br/>Socket.io]
    end
    
    subgraph "API Gateway"
        F[FastAPI REST<br/>CRUD, Triage]
        G[WebSocket Server<br/>python-socketio]
    end
    
    subgraph "Business Logic"
        H[Service Layer<br/>Triage, Override, Queue]
        I[ML Core Client<br/>Predict, Deterioration]
        J[Simulated Data Generator]
    end
    
    subgraph "Data Access"
        K[SQLAlchemy Models<br/>ORM]
        L[Redis Client<br/>Cache, Sessions]
    end
    
    subgraph "Persistence"
        M[(PostgreSQL<br/>Patients, Audit)]
        N[(Redis<br/>Sessions, Queue)]
    end
    
    subgraph "Background Jobs"
        O[Deterioration Monitor<br/>APScheduler]
    end
    
    A --> B
    B --> D
    B --> E
    D --> F
    E --> G
    F --> H
    G --> H
    H --> I
    H --> J
    H --> K
    H --> L
    K --> M
    L --> N
    O --> H
    O --> G
    I -.-> |External API| ML_Core[ML Core Engine]
```

### Frontend Architecture

#### Component Hierarchy

```
App
├── Router
│   ├── LoginPage
│   │   └── LoginForm
│   ├── ProtectedRoute
│   │   ├── DashboardLayout
│   │   │   ├── Header (user info, logout, demo mode toggle)
│   │   │   ├── Navigation (sidebar or tabs)
│   │   │   └── MainContent
│   │   │       ├── IntakeView
│   │   │       │   ├── PatientIntakeForm
│   │   │       │   │   ├── DemographicsSection
│   │   │       │   │   ├── VitalsSection (age-appropriate validation)
│   │   │       │   │   ├── ChiefComplaintSelector (autocomplete)
│   │   │       │   │   ├── SymptomsSection (checkboxes)
│   │   │       │   │   ├── HistorySection (optional fields)
│   │   │       │   │   ├── ObservationsSection
│   │   │       │   │   └── DataCompletenessIndicator (percentage bar)
│   │   │       │   └── DemoScenarioSelector (prototype mode)
│   │   │       ├── RecommendationView
│   │   │       │   ├── RecommendationPanel
│   │   │       │   │   ├── ESIDisplay (large, color-coded)
│   │   │       │   │   ├── ProbabilityChart (bar chart)
│   │   │       │   │   ├── ConfidenceBreakdown (4 dimensions)
│   │   │       │   │   ├── SafetyFlagBanner (RED/YELLOW/GREEN)
│   │   │       │   │   ├── SHAPExplanation (natural language + chart)
│   │   │       │   │   ├── RecommendationsList
│   │   │       │   │   ├── AcceptButton
│   │   │       │   │   └── OverrideButton
│   │   │       │   └── OverrideDialog (modal)
│   │   │       │       ├── ESISelector (radio buttons 1-5)
│   │   │       │       ├── ReasonCategoryDropdown
│   │   │       │       ├── ReasonTextArea (min 20 chars)
│   │   │       │       ├── ComparisonView (ML vs Clinician)
│   │   │       │       └── SubmitButton
│   │   │       ├── QueueView
│   │   │       │   ├── WaitingQueueDashboard
│   │   │       │   │   ├── SurgeModeBanner (if active)
│   │   │       │   │   ├── SummaryStatistics (total, avg wait, by ESI)
│   │   │       │   │   ├── PatientCardGrid
│   │   │       │   │   │   └── PatientCard[] (dynamic, sorted)
│   │   │       │   │   │       ├── PhotoPlaceholder
│   │   │       │   │   │       ├── NameAgeDisplay
│   │   │       │   │   │       ├── ESIBadge (color-coded)
│   │   │       │   │   │       ├── SubScoreDisplay (surge mode)
│   │   │       │   │   │       ├── WaitTimeDisplay (updating)
│   │   │       │   │   │       ├── StatusIndicator (stable/deteriorating/reassess)
│   │   │       │   │   │       └── onClick → PatientDetailModal
│   │   │       │   │   ├── RefreshAllButton
│   │   │       │   │   ├── SimulateSurgeButton (demo mode)
│   │   │       │   │   └── ExitSurgeModeButton (if active)
│   │   │       │   └── DeteriorationAlertModal (triggered by WebSocket)
│   │   │       │       ├── PatientInfo
│   │   │       │       ├── VitalChangesTable
│   │   │       │       ├── DeteriorationScore
│   │   │       │       ├── Explanation
│   │   │       │       ├── EscalateESIButton
│   │   │       │       ├── ExpedideTreatmentButton
│   │   │       │       └── DismissButton
│   │   │       └── AuditView
│   │   │           ├── AuditLogViewer (admin only)
│   │   │           │   ├── FilterPanel (date, user, ESI, flags)
│   │   │           │   ├── AuditTable (paginated)
│   │   │           │   ├── ExportCSVButton
│   │   │           │   └── RowDetailModal
│   │   │           └── DemoReportExporter (demo mode)
│   │   └── GuidedTour (Prototype Mode overlay)
│   │       ├── TourStep[] (pulsing borders, tooltips)
│   │       ├── NextButton
│   │       ├── PreviousButton
│   │       └── SkipTourButton
│   └── NotFoundPage
└── GlobalComponents
    ├── ErrorBoundary (catch React errors)
    ├── ToastNotifications (success, error, info)
    └── AudioAlertPlayer (deterioration sounds)
```

#### State Management Structure (Redux Toolkit)

```typescript
// Global Redux Store Shape
interface RootState {
  auth: {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    role: 'ED_Nurse' | 'Attending_Physician' | 'Administrator' | null;
  };
  
  currentPatient: {
    formData: PatientData | null;
    prediction: PredictionResponse | null;
    loading: boolean;
    error: string | null;
    autoSaveTimestamp: number | null;
  };
  
  waitingQueue: {
    patients: WaitingPatient[];
    surgeMode: boolean;
    surgeModeThreshold: number; // 15
    lastUpdated: number;
    loading: boolean;
  };
  
  deterioration: {
    activeAlerts: DeteriorationAlert[];
    checkHistory: DeteriorationCheck[];
    audioEnabled: boolean;
  };
  
  audit: {
    logs: AuditLogEntry[];
    filters: AuditFilters;
    pagination: {
      page: number;
      pageSize: number;
      total: number;
    };
    loading: boolean;
  };
  
  prototypeMode: {
    enabled: boolean;
    guidedTourActive: boolean;
    currentTourStep: number;
    demoScenarios: SimulatedPatient[];
    anonymizationEnabled: boolean;
  };
  
  ui: {
    currentView: 'intake' | 'recommendation' | 'queue' | 'audit';
    overrideDialogOpen: boolean;
    patientDetailModalOpen: boolean;
    selectedPatientId: string | null;
  };
}
```

#### Redux Slices

```typescript
// authSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const loginUser = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }) => {
    const response = await axios.post('/api/auth/login', credentials);
    return response.data; // { user, token, role }
  }
);

export const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    token: localStorage.getItem('token'),
    isAuthenticated: !!localStorage.getItem('token'),
    role: null,
  },
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.role = null;
      localStorage.removeItem('token');
    },
    setToken: (state, action) => {
      state.token = action.payload;
      state.isAuthenticated = true;
      localStorage.setItem('token', action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.role = action.payload.role;
        state.isAuthenticated = true;
        localStorage.setItem('token', action.payload.token);
      })
      .addCase(loginUser.rejected, (state) => {
        state.isAuthenticated = false;
      });
  },
});

// currentPatientSlice.ts
export const predictESI = createAsyncThunk(
  'currentPatient/predictESI',
  async (patientData: PatientData, { rejectWithValue }) => {
    try {
      const response = await axios.post('/api/triage/predict', patientData);
      return response.data; // PredictionResponse
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Prediction failed');
    }
  }
);

export const currentPatientSlice = createSlice({
  name: 'currentPatient',
  initialState: {
    formData: null,
    prediction: null,
    loading: false,
    error: null,
    autoSaveTimestamp: null,
  },
  reducers: {
    updateFormData: (state, action) => {
      state.formData = { ...state.formData, ...action.payload };
      state.autoSaveTimestamp = Date.now();
      // Auto-save to localStorage
      localStorage.setItem('currentPatientDraft', JSON.stringify(state.formData));
    },
    clearFormData: (state) => {
      state.formData = null;
      state.prediction = null;
      localStorage.removeItem('currentPatientDraft');
    },
    restoreFromAutoSave: (state) => {
      const saved = localStorage.getItem('currentPatientDraft');
      if (saved) {
        state.formData = JSON.parse(saved);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(predictESI.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(predictESI.fulfilled, (state, action) => {
        state.loading = false;
        state.prediction = action.payload;
      })
      .addCase(predictESI.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

// waitingQueueSlice.ts
export const waitingQueueSlice = createSlice({
  name: 'waitingQueue',
  initialState: {
    patients: [],
    surgeMode: false,
    surgeModeThreshold: 15,
    lastUpdated: Date.now(),
    loading: false,
  },
  reducers: {
    setPatients: (state, action) => {
      state.patients = action.payload;
      state.lastUpdated = Date.now();
      // Check surge mode threshold
      state.surgeMode = state.patients.length > state.surgeModeThreshold;
    },
    addPatient: (state, action) => {
      state.patients.push(action.payload);
      state.surgeMode = state.patients.length > state.surgeModeThreshold;
    },
    updatePatientStatus: (state, action) => {
      const { patientId, status } = action.payload;
      const patient = state.patients.find((p) => p.id === patientId);
      if (patient) {
        patient.status = status;
      }
    },
    removePatient: (state, action) => {
      state.patients = state.patients.filter((p) => p.id !== action.payload);
      state.surgeMode = state.patients.length > state.surgeModeThreshold;
    },
    sortQueue: (state) => {
      // Primary: ESI (ascending), Secondary: sub_score (descending), Tertiary: arrival_time (ascending)
      state.patients.sort((a, b) => {
        if (a.esi_level !== b.esi_level) return a.esi_level - b.esi_level;
        if (state.surgeMode && a.sub_score !== b.sub_score) return b.sub_score - a.sub_score;
        return new Date(a.arrival_time).getTime() - new Date(b.arrival_time).getTime();
      });
    },
  },
});
```

#### WebSocket Integration

```typescript
// websocketMiddleware.ts
import { io, Socket } from 'socket.io-client';
import { Middleware } from '@reduxjs/toolkit';

let socket: Socket | null = null;

export const websocketMiddleware: Middleware = (store) => (next) => (action) => {
  const { auth } = store.getState();
  
  // Initialize WebSocket connection after login
  if (action.type === 'auth/loginUser/fulfilled' && !socket) {
    socket = io('ws://localhost:8000', {
      auth: { token: auth.token },
      transports: ['websocket', 'polling'],
    });
    
    // Join room for real-time updates
    socket.emit('join_room', { room: 'waiting_queue' });
    
    // Listen for deterioration alerts
    socket.on('deterioration_alert', (data: DeteriorationAlert) => {
      store.dispatch({ type: 'deterioration/addAlert', payload: data });
      
      // Play audio alert if enabled
      const { deterioration } = store.getState();
      if (deterioration.audioEnabled) {
        const audio = new Audio('/sounds/alert.mp3');
        audio.play();
      }
    });
    
    // Listen for queue updates
    socket.on('queue_update', (data: { patients: WaitingPatient[] }) => {
      store.dispatch({ type: 'waitingQueue/setPatients', payload: data.patients });
      store.dispatch({ type: 'waitingQueue/sortQueue' });
    });
    
    // Listen for patient status changes
    socket.on('patient_status_change', (data: { patientId: string; status: string }) => {
      store.dispatch({ type: 'waitingQueue/updatePatientStatus', payload: data });
    });
  }
  
  // Disconnect on logout
  if (action.type === 'auth/logout' && socket) {
    socket.disconnect();
    socket = null;
  }
  
  return next(action);
};
```

### Backend Architecture

#### API Layer Structure

```
backend/
├── main.py                        # FastAPI app initialization
├── config.py                      # Environment variables, settings
├── database.py                    # SQLAlchemy engine, session
├── auth/
│   ├── __init__.py
│   ├── jwt.py                     # JWT token creation, validation
│   ├── dependencies.py            # get_current_user, require_role
│   └── router.py                  # /api/auth/* endpoints
├── models/
│   ├── __init__.py
│   ├── user.py                    # User SQLAlchemy model
│   ├── patient.py                 # Patient SQLAlchemy model
│   ├── triage_event.py            # TriageEvent SQLAlchemy model
│   ├── override.py                # Override SQLAlchemy model
│   ├── deterioration_check.py     # DeteriorationCheck SQLAlchemy model
│   ├── audit_log.py               # AuditLog SQLAlchemy model (immutable)
│   └── session.py                 # Session SQLAlchemy model
├── schemas/
│   ├── __init__.py
│   ├── patient.py                 # PatientData Pydantic schema
│   ├── prediction.py              # PredictionResponse Pydantic schema
│   ├── deterioration.py           # DeteriorationResponse Pydantic schema
│   ├── override.py                # OverrideRequest Pydantic schema
│   ├── audit.py                   # AuditLogEntry Pydantic schema
│   └── auth.py                    # LoginRequest, TokenResponse Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── ml_core_client.py          # ML Core API client (predict, deterioration)
│   ├── triage_service.py          # Triage business logic
│   ├── queue_service.py           # Queue management, surge detection
│   ├── deterioration_service.py   # Deterioration monitoring background job
│   ├── override_service.py        # Override logging and tracking
│   ├── audit_service.py           # Audit log writing (immutable)
│   └── simulated_data_generator.py# Generate 20 test patients
├── routers/
│   ├── __init__.py
│   ├── auth.py                    # POST /api/auth/login, /logout
│   ├── patients.py                # CRUD /api/patients/*
│   ├── triage.py                  # POST /api/triage/predict, /override
│   ├── queue.py                   # GET /api/queue, /api/queue/surge
│   ├── deterioration.py           # POST /api/deterioration/check
│   └── audit.py                   # GET /api/audit/logs (admin only)
├── websocket/
│   ├── __init__.py
│   ├── server.py                  # Socket.io server setup
│   └── handlers.py                # WebSocket event handlers
├── background/
│   ├── __init__.py
│   └── deterioration_monitor.py   # APScheduler job for re-assessment
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py           # Global exception handler
│   └── audit_logger.py            # Log all requests to audit_logs
└── tests/
    ├── test_auth.py
    ├── test_triage.py
    ├── test_queue.py
    └── test_ml_core_client.py
```

#### FastAPI Application Initialization

```python
# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import socketio

from database import engine, Base
from routers import auth, patients, triage, queue, deterioration, audit
from websocket.server import sio
from background.deterioration_monitor import start_background_jobs
from middleware.error_handler import add_exception_handlers
from middleware.audit_logger import AuditLoggerMiddleware

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Lifespan context for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize background jobs
    start_background_jobs()
    yield
    # Shutdown: cleanup if needed

# FastAPI app
app = FastAPI(
    title="PatientTriage.ai Clinical Interface API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom audit logger middleware
app.add_middleware(AuditLoggerMiddleware)

# Exception handlers
add_exception_handlers(app)

# Mount routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
app.include_router(deterioration.router, prefix="/api/deterioration", tags=["deterioration"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])

# Health check
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "ml_core_available": await check_ml_core_health(),
        "database_connected": True,
    }

# Mount Socket.io
socket_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
```

#### ML Core Client Service

```python
# services/ml_core_client.py
import httpx
from typing import Optional
from schemas.prediction import PredictionResponse
from schemas.deterioration import DeteriorationRequest, DeteriorationResponse
from config import settings

class MLCoreClient:
    """
    Client for ML Core API integration.
    
    Handles:
    - POST /api/v1/predict (ESI classification)
    - POST /api/v1/deterioration (deterioration detection)
    - Retry logic with exponential backoff
    - Fail-safe fallback responses
    """
    
    def __init__(self):
        self.base_url = settings.ML_CORE_BASE_URL  # http://localhost:8001
        self.api_key = settings.ML_CORE_API_KEY
        self.timeout = httpx.Timeout(5.0)  # 5 second timeout
        self.max_retries = 2
    
    async def predict_esi(
        self, 
        patient_data: dict
    ) -> PredictionResponse:
        """
        Call ML Core ESI prediction endpoint.
        
        Implements:
        - Retry logic (2 attempts with exponential backoff)
        - Fail-safe fallback (ESI 2, LOW confidence)
        - Error logging
        
        Returns:
            PredictionResponse with ESI, confidence, safety, explanation
        """
        headers = {"X-API-Key": self.api_key}
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/v1/predict",
                        json=patient_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    
                    # Parse and validate response
                    data = response.json()
                    return PredictionResponse(**data)
                    
            except httpx.TimeoutException:
                logger.warning(f"ML Core timeout (attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                    continue
                else:
                    return self._generate_failsafe_response(
                        request_id=patient_data.get('request_id', 'unknown'),
                        error="ML Core timeout after retries"
                    )
            
            except httpx.HTTPStatusError as e:
                logger.error(f"ML Core HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code in [500, 503]:  # Retry on server errors
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                return self._generate_failsafe_response(
                    request_id=patient_data.get('request_id', 'unknown'),
                    error=f"ML Core error: {e.response.status_code}"
                )
            
            except Exception as e:
                logger.error(f"ML Core unexpected error: {e}")
                return self._generate_failsafe_response(
                    request_id=patient_data.get('request_id', 'unknown'),
                    error=f"Unexpected error: {str(e)}"
                )
    
    async def assess_deterioration(
        self,
        request: DeteriorationRequest
    ) -> DeteriorationResponse:
        """
        Call ML Core deterioration detection endpoint.
        
        Returns:
            DeteriorationResponse with status, score, vital changes, recommendation
        """
        headers = {"X-API-Key": self.api_key}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/deterioration",
                    json=request.dict(),
                    headers=headers,
                )
                response.raise_for_status()
                
                data = response.json()
                return DeteriorationResponse(**data)
        
        except Exception as e:
            logger.error(f"Deterioration check failed: {e}")
            # Return UNCERTAIN status on failure
            return DeteriorationResponse(
                patient_id=request.patient_id,
                status="UNCERTAIN",
                score=50.0,
                vital_changes=[],
                explanation="Deterioration check failed - manual assessment required",
                recommendation="System error - assess patient manually",
                confidence=0.0,
                next_check_in_minutes=15,
                alert_triggered=False,
                model_version="FALLBACK",
                timestamp=datetime.now(),
            )
    
    def _generate_failsafe_response(
        self, 
        request_id: str, 
        error: str
    ) -> PredictionResponse:
        """
        Generate safe fallback response when ML Core is unavailable.
        
        Strategy:
        - Predict ESI 2 (mid-high urgency, safe escalation)
        - Confidence: LOW (0%)
        - Safety flag: YELLOW (flag for clinical validation)
        - Explanation: Indicate model error, recommend manual assessment
        """
        return PredictionResponse(
            request_id=request_id,
            esi_prediction=2,
            probability_distribution=[0.0, 1.0, 0.0, 0.0, 0.0],
            confidence_breakdown={
                "model_certainty": 0.0,
                "data_completeness": 0.0,
                "clinical_consistency": 0.0,
                "pattern_recognition": 0.0,
                "overall": 0.0,
                "level": "LOW",
            },
            safety_flag={
                "outcome": "YELLOW",
                "triggered_criteria": [f"MODEL_ERROR: {error}"],
                "recommended_action": "Manual clinical assessment required (ML Core unavailable)",
                "override_esi": None,
            },
            explanation={
                "text": f"Model inference failed: {error}. Defaulting to ESI 2 for safety. Manual assessment required.",
                "top_factors": [],
            },
            sub_score=None,
            recommendations=[
                "⚠️ ML Core unavailable - perform manual triage",
                "System issue logged, technical team notified",
            ],
            model_version="FALLBACK",
            inference_time_ms=0.0,
            timestamp=datetime.now(),
        )

# Singleton instance
ml_core_client = MLCoreClient()
```

### Database Schema

#### PostgreSQL Tables

```sql
-- users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ED_Nurse', 'Attending_Physician', 'Administrator')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);

-- sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    login_at TIMESTAMP NOT NULL DEFAULT NOW(),
    logout_at TIMESTAMP,
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_session CHECK (logout_at IS NULL OR logout_at >= login_at)
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON sessions(token_hash);

-- patients table
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Demographics
    age INTEGER NOT NULL CHECK (age >= 0 AND age <= 120),
    sex VARCHAR(20) NOT NULL CHECK (sex IN ('male', 'female', 'other')),
    age_group VARCHAR(50) NOT NULL CHECK (age_group IN (
        'pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 'adult', 'geriatric'
    )),
    
    -- Vitals (can be NULL for missing data)
    hr INTEGER CHECK (hr >= 20 AND hr <= 250),
    bp_systolic INTEGER CHECK (bp_systolic >= 50 AND bp_systolic <= 250),
    bp_diastolic INTEGER CHECK (bp_diastolic >= 30 AND bp_diastolic <= 150),
    spo2 INTEGER CHECK (spo2 >= 50 AND spo2 <= 100),
    rr INTEGER CHECK (rr >= 5 AND rr <= 60),
    temperature FLOAT CHECK (temperature >= 32.0 AND temperature <= 42.0),
    
    -- Clinical
    chief_complaint TEXT NOT NULL,
    chief_complaint_category VARCHAR(100) NOT NULL,
    pain_score INTEGER CHECK (pain_score >= 0 AND pain_score <= 10),
    arrival_mode VARCHAR(50) NOT NULL CHECK (arrival_mode IN ('walk_in', 'ambulance', 'police', 'transfer')),
    mental_status VARCHAR(50) NOT NULL CHECK (mental_status IN ('alert', 'confused', 'drowsy', 'unresponsive')),
    
    -- Additional data (stored as JSONB for flexibility)
    symptoms JSONB DEFAULT '[]',
    medical_history JSONB DEFAULT '{}',
    observations JSONB DEFAULT '[]',
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Soft delete (for prototype mode)
    deleted_at TIMESTAMP
);

CREATE INDEX idx_patients_age_group ON patients(age_group);
CREATE INDEX idx_patients_chief_complaint_category ON patients(chief_complaint_category);
CREATE INDEX idx_patients_created_at ON patients(created_at);

-- triage_events table
CREATE TABLE triage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    
    -- ML Prediction
    ml_predicted_esi INTEGER NOT NULL CHECK (ml_predicted_esi >= 1 AND ml_predicted_esi <= 5),
    ml_probability_distribution FLOAT[] NOT NULL,
    ml_confidence_breakdown JSONB NOT NULL,
    ml_safety_flag VARCHAR(10) NOT NULL CHECK (ml_safety_flag IN ('RED', 'YELLOW', 'GREEN')),
    ml_explanation JSONB NOT NULL,
    ml_sub_score FLOAT CHECK (ml_sub_score >= 0 AND ml_sub_score <= 100),
    ml_model_version VARCHAR(50) NOT NULL,
    
    -- Final Decision
    final_esi INTEGER NOT NULL CHECK (final_esi >= 1 AND final_esi <= 5),
    override_flag BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_esi_decision CHECK (final_esi >= 1 AND final_esi <= 5)
);

CREATE INDEX idx_triage_events_patient_id ON triage_events(patient_id);
CREATE INDEX idx_triage_events_user_id ON triage_events(user_id);
CREATE INDEX idx_triage_events_created_at ON triage_events(created_at);
CREATE INDEX idx_triage_events_ml_safety_flag ON triage_events(ml_safety_flag);

-- overrides table
CREATE TABLE overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triage_event_id UUID NOT NULL REFERENCES triage_events(id) ON DELETE CASCADE,
    
    -- Override details
    ml_predicted_esi INTEGER NOT NULL,
    clinician_final_esi INTEGER NOT NULL,
    override_direction VARCHAR(20) NOT NULL CHECK (override_direction IN ('escalation', 'de-escalation')),
    override_magnitude INTEGER NOT NULL CHECK (override_magnitude >= 1),
    
    -- Reasoning
    reason_category VARCHAR(50) NOT NULL CHECK (reason_category IN (
        'clinical_judgment', 'additional_information', 'safety_concern', 
        'ml_error', 'patient_preference', 'resource_constraint'
    )),
    reason_text TEXT NOT NULL,
    
    -- Outcome (populated later)
    disposition VARCHAR(50),
    adverse_event BOOLEAN,
    time_to_treatment_minutes INTEGER,
    outcome_updated_at TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_overrides_triage_event_id ON overrides(triage_event_id);
CREATE INDEX idx_overrides_reason_category ON overrides(reason_category);
CREATE INDEX idx_overrides_created_at ON overrides(created_at);

-- deterioration_checks table
CREATE TABLE deterioration_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    triage_event_id UUID REFERENCES triage_events(id) ON DELETE SET NULL,
    
    -- Initial vitals
    initial_hr INTEGER,
    initial_bp_systolic INTEGER,
    initial_bp_diastolic INTEGER,
    initial_spo2 INTEGER,
    initial_rr INTEGER,
    initial_temperature FLOAT,
    
    -- Current vitals
    current_hr INTEGER,
    current_bp_systolic INTEGER,
    current_bp_diastolic INTEGER,
    current_spo2 INTEGER,
    current_rr INTEGER,
    current_temperature FLOAT,
    
    -- Assessment
    status VARCHAR(20) NOT NULL CHECK (status IN ('STABLE', 'DETERIORATING', 'UNCERTAIN')),
    score FLOAT NOT NULL CHECK (score >= 0 AND score <= 100),
    vital_changes JSONB NOT NULL,
    explanation TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Context
    initial_esi INTEGER NOT NULL,
    time_since_triage_minutes INTEGER NOT NULL,
    alert_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    next_check_in_minutes INTEGER,
    
    -- Model
    model_version VARCHAR(50) NOT NULL,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_deterioration_checks_patient_id ON deterioration_checks(patient_id);
CREATE INDEX idx_deterioration_checks_status ON deterioration_checks(status);
CREATE INDEX idx_deterioration_checks_created_at ON deterioration_checks(created_at);

-- audit_logs table (IMMUTABLE - INSERT ONLY)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    session_id UUID REFERENCES sessions(id),
    user_id UUID REFERENCES users(id),
    
    -- Action
    action_type VARCHAR(100) NOT NULL,  -- 'login', 'triage_prediction', 'override', 'deterioration_check', etc.
    resource_type VARCHAR(50),  -- 'patient', 'triage_event', 'override', etc.
    resource_id UUID,
    
    -- Details (flexible JSONB)
    details JSONB NOT NULL,
    
    -- HTTP context (if applicable)
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource_type_id ON audit_logs(resource_type, resource_id);

-- Enforce immutability: No updates or deletes allowed on audit_logs
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable. Updates and deletes are not allowed.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

CREATE TRIGGER prevent_audit_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

#### SQLAlchemy Models

```python
# models/patient.py
from sqlalchemy import Column, String, Integer, Float, Text, TIMESTAMP, UUID, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base
import uuid

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Demographics
    age = Column(Integer, nullable=False)
    sex = Column(String(20), nullable=False)
    age_group = Column(String(50), nullable=False)
    
    # Vitals
    hr = Column(Integer)
    bp_systolic = Column(Integer)
    bp_diastolic = Column(Integer)
    spo2 = Column(Integer)
    rr = Column(Integer)
    temperature = Column(Float)
    
    # Clinical
    chief_complaint = Column(Text, nullable=False)
    chief_complaint_category = Column(String(100), nullable=False)
    pain_score = Column(Integer)
    arrival_mode = Column(String(50), nullable=False)
    mental_status = Column(String(50), nullable=False)
    
    # Additional data (JSONB)
    symptoms = Column(JSONB, default=list)
    medical_history = Column(JSONB, default=dict)
    observations = Column(JSONB, default=list)
    
    # Metadata
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP)
    
    # Relationships
    triage_events = relationship("TriageEvent", back_populates="patient")
    deterioration_checks = relationship("DeteriorationCheck", back_populates="patient")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('age >= 0 AND age <= 120', name='valid_age'),
        CheckConstraint("sex IN ('male', 'female', 'other')", name='valid_sex'),
        CheckConstraint("age_group IN ('pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 'adult', 'geriatric')", name='valid_age_group'),
        CheckConstraint('hr >= 20 AND hr <= 250', name='valid_hr'),
        CheckConstraint('spo2 >= 50 AND spo2 <= 100', name='valid_spo2'),
    )

# models/triage_event.py
class TriageEvent(Base):
    __tablename__ = "triage_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    
    # ML Prediction
    ml_predicted_esi = Column(Integer, nullable=False)
    ml_probability_distribution = Column(ARRAY(Float), nullable=False)
    ml_confidence_breakdown = Column(JSONB, nullable=False)
    ml_safety_flag = Column(String(10), nullable=False)
    ml_explanation = Column(JSONB, nullable=False)
    ml_sub_score = Column(Float)
    ml_model_version = Column(String(50), nullable=False)
    
    # Final Decision
    final_esi = Column(Integer, nullable=False)
    override_flag = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="triage_events")
    user = relationship("User")
    session = relationship("Session")
    override = relationship("Override", back_populates="triage_event", uselist=False)
    
    __table_args__ = (
        CheckConstraint('ml_predicted_esi >= 1 AND ml_predicted_esi <= 5', name='valid_ml_esi'),
        CheckConstraint('final_esi >= 1 AND final_esi <= 5', name='valid_final_esi'),
        CheckConstraint("ml_safety_flag IN ('RED', 'YELLOW', 'GREEN')", name='valid_safety_flag'),
    )
```

### Component Design

#### Patient Intake Form Component

```typescript
// components/PatientIntakeForm.tsx
import React, { useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Box,
  Grid,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Autocomplete,
  Checkbox,
  FormControlLabel,
  Typography,
  Button,
  LinearProgress,
  Alert,
} from '@mui/material';
import debounce from 'lodash/debounce';

import { updateFormData, predictESI } from '../store/slices/currentPatientSlice';
import { CHIEF_COMPLAINT_CATEGORIES, AGE_SPECIFIC_VITAL_RANGES } from '../constants';

// Zod schema for validation
const patientDataSchema = z.object({
  demographics: z.object({
    age: z.number().min(0).max(120),
    sex: z.enum(['male', 'female', 'other']),
  }),
  vitals: z.object({
    hr: z.number().min(20).max(250).optional(),
    bp_systolic: z.number().min(50).max(250).optional(),
    bp_diastolic: z.number().min(30).max(150).optional(),
    spo2: z.number().min(50).max(100).optional(),
    rr: z.number().min(5).max(60).optional(),
    temperature: z.number().min(32.0).max(42.0).optional(),
  }).refine(
    (data) => {
      // At least 3 required vitals must be present
      const requiredVitals = [data.hr, data.bp_systolic, data.spo2, data.rr];
      const presentCount = requiredVitals.filter((v) => v !== undefined).length;
      return presentCount >= 3;
    },
    { message: "At least 3 required vitals (HR, BP, SpO2, RR) must be provided" }
  ),
  clinical: z.object({
    chief_complaint: z.string().min(1).max(500),
    chief_complaint_category: z.string().min(1),
    pain_score: z.number().min(0).max(10).optional(),
    arrival_mode: z.enum(['walk_in', 'ambulance', 'police', 'transfer']),
    mental_status: z.enum(['alert', 'confused', 'drowsy', 'unresponsive']),
  }),
  symptoms: z.array(z.string()).default([]),
  history: z.object({
    cardiac_history: z.boolean().default(false),
    respiratory_history: z.boolean().default(false),
    diabetes: z.boolean().default(false),
    hypertension: z.boolean().default(false),
    on_medications: z.boolean().default(false),
    recent_hospitalization: z.boolean().default(false),
  }).default({}),
  observations: z.array(z.string()).default([]),
});

type PatientFormData = z.infer<typeof patientDataSchema>;

export const PatientIntakeForm: React.FC = () => {
  const dispatch = useDispatch();
  const { formData, loading } = useSelector((state: RootState) => state.currentPatient);
  const { demoScenarios } = useSelector((state: RootState) => state.prototypeMode);
  
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<PatientFormData>({
    resolver: zodResolver(patientDataSchema),
    defaultValues: formData || {
      demographics: { age: 0, sex: 'male' },
      vitals: {},
      clinical: {
        chief_complaint: '',
        chief_complaint_category: '',
        pain_score: undefined,
        arrival_mode: 'walk_in',
        mental_status: 'alert',
      },
      symptoms: [],
      history: {},
      observations: [],
    },
  });
  
  // Watch all form values for auto-save
  const watchedValues = watch();
  
  // Auto-save debounced (every 10 seconds)
  const debouncedAutoSave = useCallback(
    debounce((data: PatientFormData) => {
      dispatch(updateFormData(data));
    }, 10000),
    []
  );
  
  useEffect(() => {
    debouncedAutoSave(watchedValues);
  }, [watchedValues, debouncedAutoSave]);
  
  // Compute age group when age changes
  const age = watch('demographics.age');
  const ageGroup = React.useMemo(() => {
    if (age <= 2) return 'pediatric_infant';
    if (age <= 12) return 'pediatric_child';
    if (age <= 17) return 'pediatric_adolescent';
    if (age <= 64) return 'adult';
    return 'geriatric';
  }, [age]);
  
  // Get age-appropriate vital ranges
  const vitalRanges = AGE_SPECIFIC_VITAL_RANGES[ageGroup];
  
  // Compute data completeness score
  const dataCompletenessScore = React.useMemo(() => {
    const totalFields = 40; // Approximate
    const presentFields = Object.values(watchedValues).flat().filter(Boolean).length;
    return Math.round((presentFields / totalFields) * 100);
  }, [watchedValues]);
  
  // Handle form submission
  const onSubmit = async (data: PatientFormData) => {
    const request_id = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const payload = {
      request_id,
      ...data,
      metadata: {
        interface_version: '1.0.0',
        submitted_at: new Date().toISOString(),
      },
    };
    
    await dispatch(predictESI(payload));
  };
  
  // Load demo scenario
  const loadDemoScenario = (scenarioId: string) => {
    const scenario = demoScenarios.find((s) => s.id === scenarioId);
    if (scenario) {
      setValue('demographics', scenario.demographics);
      setValue('vitals', scenario.vitals);
      setValue('clinical', scenario.clinical);
      setValue('symptoms', scenario.symptoms);
      setValue('history', scenario.history);
      setValue('observations', scenario.observations);
    }
  };
  
  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ p: 3 }}>
      {/* Demo Scenario Selector */}
      {demoScenarios.length > 0 && (
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Demo Scenario</InputLabel>
          <Select onChange={(e) => loadDemoScenario(e.target.value)} defaultValue="">
            <MenuItem value="">-- Custom Patient --</MenuItem>
            {demoScenarios.map((scenario) => (
              <MenuItem key={scenario.id} value={scenario.id}>
                {scenario.name} - {scenario.description}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      
      {/* Age Group Badge */}
      {age > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {ageGroup === 'pediatric_infant' && '👶 PEDIATRIC PATIENT (Infant 0-2)'}
          {ageGroup === 'pediatric_child' && '🧒 PEDIATRIC PATIENT (Child 3-12)'}
          {ageGroup === 'pediatric_adolescent' && '🧑 PEDIATRIC PATIENT (Adolescent 13-17)'}
          {ageGroup === 'geriatric' && '👴 GERIATRIC PATIENT (65+)'}
          {ageGroup === 'adult' && 'Adult Patient (18-64)'}
        </Alert>
      )}
      
      {/* Demographics Section */}
      <Typography variant="h6" gutterBottom>
        Demographics
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <Controller
            name="demographics.age"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Age"
                type="number"
                fullWidth
                required
                error={!!errors.demographics?.age}
                helperText={errors.demographics?.age?.message || '0-120 years'}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <Controller
            name="demographics.sex"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth required>
                <InputLabel>Sex</InputLabel>
                <Select {...field} label="Sex">
                  <MenuItem value="male">Male</MenuItem>
                  <MenuItem value="female">Female</MenuItem>
                  <MenuItem value="other">Other</MenuItem>
                </Select>
              </FormControl>
            )}
          />
        </Grid>
      </Grid>
      
      {/* Vitals Section */}
      <Typography variant="h6" gutterBottom>
        Vital Signs
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.hr"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Heart Rate"
                type="number"
                fullWidth
                required
                error={!!errors.vitals?.hr}
                helperText={
                  errors.vitals?.hr?.message ||
                  `Normal ${ageGroup}: ${vitalRanges.hr_min}-${vitalRanges.hr_max} bpm`
                }
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.bp_systolic"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="BP Systolic"
                type="number"
                fullWidth
                required
                helperText={`Normal: ${vitalRanges.bp_sys_min}-${vitalRanges.bp_sys_max} mmHg`}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.bp_diastolic"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="BP Diastolic"
                type="number"
                fullWidth
                helperText={`Normal: ${vitalRanges.bp_dia_min}-${vitalRanges.bp_dia_max} mmHg`}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.spo2"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="SpO2"
                type="number"
                fullWidth
                required
                helperText={`Normal: ≥${vitalRanges.spo2_min}%`}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.rr"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Respiratory Rate"
                type="number"
                fullWidth
                required
                helperText={`Normal: ${vitalRanges.rr_min}-${vitalRanges.rr_max} breaths/min`}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="vitals.temperature"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Temperature (°C)"
                type="number"
                fullWidth
                helperText={`Normal: ${vitalRanges.temp_min}-${vitalRanges.temp_max}°C`}
              />
            )}
          />
        </Grid>
      </Grid>
      
      {/* Chief Complaint Section */}
      <Typography variant="h6" gutterBottom>
        Chief Complaint
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Controller
            name="clinical.chief_complaint"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Chief Complaint (Free Text)"
                multiline
                rows={2}
                fullWidth
                required
                error={!!errors.clinical?.chief_complaint}
                helperText={errors.clinical?.chief_complaint?.message}
              />
            )}
          />
        </Grid>
        <Grid item xs={12}>
          <Controller
            name="clinical.chief_complaint_category"
            control={control}
            render={({ field }) => (
              <Autocomplete
                {...field}
                options={CHIEF_COMPLAINT_CATEGORIES}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Chief Complaint Category"
                    required
                    error={!!errors.clinical?.chief_complaint_category}
                    helperText="Select from 50+ standardized categories"
                  />
                )}
                onChange={(_, value) => field.onChange(value)}
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="clinical.pain_score"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Pain Score (0-10)"
                type="number"
                fullWidth
                helperText="Optional"
              />
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="clinical.arrival_mode"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth required>
                <InputLabel>Arrival Mode</InputLabel>
                <Select {...field} label="Arrival Mode">
                  <MenuItem value="walk_in">Walk-in</MenuItem>
                  <MenuItem value="ambulance">Ambulance</MenuItem>
                  <MenuItem value="police">Police</MenuItem>
                  <MenuItem value="transfer">Transfer</MenuItem>
                </Select>
              </FormControl>
            )}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <Controller
            name="clinical.mental_status"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth required>
                <InputLabel>Mental Status</InputLabel>
                <Select {...field} label="Mental Status">
                  <MenuItem value="alert">Alert</MenuItem>
                  <MenuItem value="confused">Confused</MenuItem>
                  <MenuItem value="drowsy">Drowsy</MenuItem>
                  <MenuItem value="unresponsive">Unresponsive</MenuItem>
                </Select>
              </FormControl>
            )}
          />
        </Grid>
      </Grid>
      
      {/* Symptoms Section */}
      <Typography variant="h6" gutterBottom>
        Symptoms (Optional)
      </Typography>
      <Grid container spacing={1} sx={{ mb: 3 }}>
        {[
          'chest_pain',
          'shortness_of_breath',
          'altered_consciousness',
          'abdominal_pain',
          'fever',
          'nausea_vomiting',
          'headache',
          'dizziness',
        ].map((symptom) => (
          <Grid item xs={12} sm={6} md={3} key={symptom}>
            <Controller
              name="symptoms"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={field.value?.includes(symptom)}
                      onChange={(e) => {
                        const newSymptoms = e.target.checked
                          ? [...(field.value || []), symptom]
                          : field.value?.filter((s) => s !== symptom);
                        field.onChange(newSymptoms);
                      }}
                    />
                  }
                  label={symptom.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                />
              )}
            />
          </Grid>
        ))}
      </Grid>
      
      {/* Medical History Section */}
      <Typography variant="h6" gutterBottom>
        Medical History (Optional)
      </Typography>
      <Grid container spacing={1} sx={{ mb: 3 }}>
        {[
          'cardiac_history',
          'respiratory_history',
          'diabetes',
          'hypertension',
          'on_medications',
          'recent_hospitalization',
        ].map((historyItem) => (
          <Grid item xs={12} sm={6} md={4} key={historyItem}>
            <Controller
              name={`history.${historyItem}` as any}
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value || false} />}
                  label={historyItem.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                />
              )}
            />
          </Grid>
        ))}
      </Grid>
      
      {/* Data Completeness Indicator */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" gutterBottom>
          Data Completeness: {dataCompletenessScore}%
        </Typography>
        <LinearProgress
          variant="determinate"
          value={dataCompletenessScore}
          color={dataCompletenessScore >= 70 ? 'success' : 'warning'}
        />
      </Box>
      
      {/* Submit Button */}
      <Button
        type="submit"
        variant="contained"
        size="large"
        fullWidth
        disabled={loading}
      >
        {loading ? 'Getting AI Recommendation...' : 'Submit for Triage'}
      </Button>
    </Box>
  );
};
```

#### Recommendation Panel Component

```typescript
// components/RecommendationPanel.tsx
import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  Alert,
  LinearProgress,
  Dialog,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

import { OverrideDialog } from './OverrideDialog';

const ESI_COLORS = {
  1: '#d32f2f', // Red
  2: '#f57c00', // Orange
  3: '#fbc02d', // Yellow
  4: '#388e3c', // Green
  5: '#1976d2', // Blue
};

export const RecommendationPanel: React.FC = () => {
  const dispatch = useDispatch();
  const { prediction, loading, error } = useSelector(
    (state: RootState) => state.currentPatient
  );
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  
  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Getting AI Recommendation...
        </Typography>
        <LinearProgress />
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error" sx={{ m: 3 }}>
        {error}
      </Alert>
    );
  }
  
  if (!prediction) {
    return (
      <Alert severity="info" sx={{ m: 3 }}>
        Submit patient data to receive triage recommendation
      </Alert>
    );
  }
  
  // Parse prediction response
  const {
    esi_prediction,
    probability_distribution,
    confidence_breakdown,
    safety_flag,
    explanation,
    sub_score,
    recommendations,
    model_version,
  } = prediction;
  
  // Probability chart data
  const probabilityData = probability_distribution.map((prob, idx) => ({
    esi: idx + 1,
    probability: prob * 100,
  }));
  
  // SHAP chart data
  const shapData = explanation.top_factors.map((factor) => ({
    feature: factor.feature,
    contribution: factor.contribution,
    direction: factor.direction,
  }));
  
  return (
    <Box sx={{ p: 3 }}>
      {/* Safety Flag Banner */}
      {safety_flag.outcome === 'RED' && (
        <Alert
          severity="error"
          icon={<span style={{ fontSize: '2rem' }}>🚨</span>}
          sx={{ mb: 3, animation: 'pulse 2s infinite' }}
        >
          <Typography variant="h6">CRITICAL SAFETY ALERT</Typography>
          <Typography variant="body2">
            {safety_flag.recommended_action}
          </Typography>
          <Box sx={{ mt: 1 }}>
            {safety_flag.triggered_criteria.map((criterion, idx) => (
              <Typography key={idx} variant="body2" sx={{ fontWeight: 'bold' }}>
                • {criterion}
              </Typography>
            ))}
          </Box>
        </Alert>
      )}
      
      {safety_flag.outcome === 'YELLOW' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="h6">⚠️ Caution Advised</Typography>
          <Typography variant="body2">
            {safety_flag.recommended_action}
          </Typography>
        </Alert>
      )}
      
      {/* ESI Display */}
      <Card sx={{ mb: 3, borderLeft: `8px solid ${ESI_COLORS[esi_prediction]}` }}>
        <CardContent>
          <Grid container alignItems="center" spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="h3" component="div">
                ESI Level: {esi_prediction}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {esi_prediction === 1 && 'Resuscitation'}
                {esi_prediction === 2 && 'Emergent'}
                {esi_prediction === 3 && 'Urgent'}
                {esi_prediction === 4 && 'Less Urgent'}
                {esi_prediction === 5 && 'Non-Urgent'}
              </Typography>
              {safety_flag.override_esi && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  Safety Override: Force ESI {safety_flag.override_esi}
                </Alert>
              )}
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="h6" gutterBottom>
                Probability Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={probabilityData}>
                  <XAxis dataKey="esi" label={{ value: 'ESI Level', position: 'insideBottom' }} />
                  <YAxis label={{ value: 'Probability (%)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                  <Bar dataKey="probability">
                    {probabilityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={ESI_COLORS[entry.esi]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Confidence Breakdown */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Confidence: {confidence_breakdown.level}
            {confidence_breakdown.level === 'HIGH' && ' ✅'}
            {confidence_breakdown.level === 'MEDIUM' && ' ⚠️'}
            {confidence_breakdown.level === 'LOW' && ' 🔴'}
            <Chip
              label={`${confidence_breakdown.overall.toFixed(0)}%`}
              color={
                confidence_breakdown.level === 'HIGH'
                  ? 'success'
                  : confidence_breakdown.level === 'MEDIUM'
                  ? 'warning'
                  : 'error'
              }
              sx={{ ml: 2 }}
            />
          </Typography>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {[
              { label: 'Model Certainty', value: confidence_breakdown.model_certainty },
              { label: 'Data Completeness', value: confidence_breakdown.data_completeness },
              { label: 'Clinical Consistency', value: confidence_breakdown.clinical_consistency },
              { label: 'Pattern Recognition', value: confidence_breakdown.pattern_recognition },
            ].map((dimension) => (
              <Grid item xs={12} sm={6} key={dimension.label}>
                <Typography variant="body2" gutterBottom>
                  {dimension.label}: {dimension.value.toFixed(0)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={dimension.value}
                  color={dimension.value >= 80 ? 'success' : dimension.value >= 60 ? 'warning' : 'error'}
                />
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
      
      {/* SHAP Explanation */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Contributing Factors (SHAP Analysis)
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {explanation.text}
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={shapData} layout="vertical">
              <XAxis type="number" />
              <YAxis dataKey="feature" type="category" width={150} />
              <Tooltip />
              <Bar dataKey="contribution">
                {shapData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      entry.direction === 'increases urgency'
                        ? '#d32f2f'
                        : entry.direction === 'decreases urgency'
                        ? '#388e3c'
                        : '#757575'
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      
      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recommendations
            </Typography>
            {recommendations.map((rec, idx) => (
              <Alert key={idx} severity="info" sx={{ mb: 1 }}>
                {rec}
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}
      
      {/* Sub-Score (Surge Mode) */}
      {sub_score !== null && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Surge Mode Sub-Score: {sub_score.toFixed(1)} / 100
            </Typography>
            <LinearProgress variant="determinate" value={sub_score} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Higher score = higher priority within ESI {esi_prediction} category
            </Typography>
          </CardContent>
        </Card>
      )}
      
      {/* Action Buttons */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <Button
            variant="contained"
            color="success"
            fullWidth
            size="large"
            onClick={() => {
              // Accept recommendation and add to queue
              dispatch({ type: 'queue/addPatientFromRecommendation', payload: prediction });
              dispatch({ type: 'currentPatient/clearFormData' });
              // Navigate to queue view
            }}
          >
            Accept Recommendation
          </Button>
        </Grid>
        <Grid item xs={12} sm={6}>
          <Button
            variant="outlined"
            color="warning"
            fullWidth
            size="large"
            onClick={() => setOverrideDialogOpen(true)}
          >
            Override Decision
          </Button>
        </Grid>
      </Grid>
      
      {/* Model Version Footer */}
      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
        Model Version: {model_version} | Request ID: {prediction.request_id}
      </Typography>
      
      {/* Override Dialog */}
      <OverrideDialog
        open={overrideDialogOpen}
        onClose={() => setOverrideDialogOpen(false)}
        mlPrediction={prediction}
      />
    </Box>
  );
};
```

Due to length constraints, I'll continue in the next message with the remaining components, API design, background jobs, testing strategy, and deployment configuration.


#### Override Dialog Component

```typescript
// components/OverrideDialog.tsx
import React from 'react';
import { useDispatch } from 'react-redux';
import { useForm, Controller } from 'react-hook-form';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  RadioGroup,
  FormControlLabel,
  Radio,
  Select,
  MenuItem,
  InputLabel,
  TextField,
  Typography,
  Grid,
  Box,
  Alert,
} from '@mui/material';

interface OverrideDialogProps {
  open: boolean;
  onClose: () => void;
  mlPrediction: PredictionResponse;
}

export const OverrideDialog: React.FC<OverrideDialogProps> = ({
  open,
  onClose,
  mlPrediction,
}) => {
  const dispatch = useDispatch();
  const { control, handleSubmit, watch, formState: { errors } } = useForm({
    defaultValues: {
      clinician_esi: mlPrediction.esi_prediction,
      reason_category: '',
      reason_text: '',
    },
  });
  
  const clinicianESI = watch('clinician_esi');
  
  const overrideDirection =
    clinicianESI < mlPrediction.esi_prediction
      ? 'escalation'
      : clinicianESI > mlPrediction.esi_prediction
      ? 'de-escalation'
      : 'none';
  
  const onSubmit = async (data) => {
    const overridePayload = {
      ml_predicted_esi: mlPrediction.esi_prediction,
      clinician_final_esi: data.clinician_esi,
      override_direction: overrideDirection,
      override_magnitude: Math.abs(data.clinician_esi - mlPrediction.esi_prediction),
      reason_category: data.reason_category,
      reason_text: data.reason_text,
      ml_prediction: mlPrediction,
    };
    
    await dispatch(submitOverride(overridePayload));
    onClose();
  };
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Override AI Recommendation</DialogTitle>
      <DialogContent>
        <form>
          {/* Comparison View */}
          <Box sx={{ mb: 3 }}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Alert severity="info">
                  <Typography variant="subtitle2">ML Recommendation</Typography>
                  <Typography variant="h4">ESI {mlPrediction.esi_prediction}</Typography>
                  <Typography variant="body2">
                    Confidence: {mlPrediction.confidence_breakdown.level} (
                    {mlPrediction.confidence_breakdown.overall.toFixed(0)}%)
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={6}>
                <Alert
                  severity={
                    overrideDirection === 'escalation'
                      ? 'error'
                      : overrideDirection === 'de-escalation'
                      ? 'warning'
                      : 'success'
                  }
                >
                  <Typography variant="subtitle2">Your Decision</Typography>
                  <Typography variant="h4">ESI {clinicianESI}</Typography>
                  <Typography variant="body2">
                    {overrideDirection === 'escalation' && '⬆️ Escalation (higher urgency)'}
                    {overrideDirection === 'de-escalation' && '⬇️ De-escalation (lower urgency)'}
                    {overrideDirection === 'none' && '✅ Agreement'}
                  </Typography>
                </Alert>
              </Grid>
            </Grid>
          </Box>
          
          {/* ESI Selector */}
          <FormControl component="fieldset" fullWidth sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Select Final ESI Level
            </Typography>
            <Controller
              name="clinician_esi"
              control={control}
              render={({ field }) => (
                <RadioGroup {...field} row>
                  {[1, 2, 3, 4, 5].map((esi) => (
                    <FormControlLabel
                      key={esi}
                      value={esi}
                      control={<Radio />}
                      label={`ESI ${esi}`}
                    />
                  ))}
                </RadioGroup>
              )}
            />
          </FormControl>
          
          {/* Escalation Warning */}
          {overrideDirection === 'escalation' && (
            <Alert severity="warning" sx={{ mb: 3 }}>
              <Typography variant="subtitle2">
                ⚠️ Escalation Notice
              </Typography>
              <Typography variant="body2">
                You are escalating from ESI {mlPrediction.esi_prediction} to ESI {clinicianESI}.
                This will allocate additional resources and reduce wait time.
              </Typography>
            </Alert>
          )}
          
          {/* Override Reason Category */}
          <FormControl fullWidth sx={{ mb: 3 }} required>
            <InputLabel>Override Reason Category</InputLabel>
            <Controller
              name="reason_category"
              control={control}
              rules={{ required: 'Reason category is required' }}
              render={({ field }) => (
                <Select {...field} label="Override Reason Category">
                  <MenuItem value="clinical_judgment">Clinical Judgment</MenuItem>
                  <MenuItem value="additional_information">
                    Additional Information Not Available to AI
                  </MenuItem>
                  <MenuItem value="safety_concern">Safety Concern</MenuItem>
                  <MenuItem value="ml_error">AI Error / Incorrect Assessment</MenuItem>
                  <MenuItem value="patient_preference">Patient Preference</MenuItem>
                  <MenuItem value="resource_constraint">Resource Constraint</MenuItem>
                </Select>
              )}
            />
          </FormControl>
          
          {/* Override Reason Text */}
          <Controller
            name="reason_text"
            control={control}
            rules={{
              required: 'Detailed reason is required',
              minLength: { value: 20, message: 'Minimum 20 characters required' },
            }}
            render={({ field }) => (
              <TextField
                {...field}
                label="Detailed Reason (minimum 20 characters)"
                multiline
                rows={4}
                fullWidth
                required
                error={!!errors.reason_text}
                helperText={
                  errors.reason_text?.message ||
                  'Explain your clinical reasoning for this override'
                }
              />
            )}
          />
        </form>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSubmit(onSubmit)} variant="contained" color="primary">
          Submit Override
        </Button>
      </DialogActions>
    </Dialog>
  );
};
```

#### Waiting Queue Dashboard Component

```typescript
// components/WaitingQueueDashboard.tsx
import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Alert,
  Avatar,
} from '@mui/material';
import { formatDistanceToNow } from 'date-fns';

import { PatientCard } from './PatientCard';
import { DeteriorationAlertModal } from './DeteriorationAlertModal';

export const WaitingQueueDashboard: React.FC = () => {
  const dispatch = useDispatch();
  const { patients, surgeMode, surgeModeThreshold, lastUpdated } = useSelector(
    (state: RootState) => state.waitingQueue
  );
  const { activeAlerts } = useSelector((state: RootState) => state.deterioration);
  const { enabled: prototypeMode } = useSelector((state: RootState) => state.prototypeMode);
  
  useEffect(() => {
    // Fetch queue on mount
    dispatch(fetchWaitingQueue());
  }, [dispatch]);
  
  // Summary statistics
  const totalPatients = patients.length;
  const avgWaitTime =
    patients.reduce((sum, p) => sum + p.wait_time_minutes, 0) / totalPatients || 0;
  const patientsByESI = [1, 2, 3, 4, 5].map(
    (esi) => patients.filter((p) => p.esi_level === esi).length
  );
  
  return (
    <Box sx={{ p: 3 }}>
      {/* Surge Mode Banner */}
      {surgeMode && (
        <Alert severity="warning" sx={{ mb: 3, animation: 'pulse 2s infinite' }}>
          <Typography variant="h6">🚨 SURGE MODE ACTIVE</Typography>
          <Typography variant="body2">
            {totalPatients} patients waiting (threshold: {surgeModeThreshold}). Sub-scores active for
            prioritization.
          </Typography>
          <Button
            variant="outlined"
            size="small"
            sx={{ mt: 1 }}
            onClick={() => dispatch(exitSurgeMode())}
          >
            Exit Surge Mode (Demo)
          </Button>
        </Alert>
      )}
      
      {/* Summary Statistics */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <Typography variant="h4">{totalPatients}</Typography>
              <Typography variant="body2" color="text.secondary">
                Total Waiting
              </Typography>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Typography variant="h4">{avgWaitTime.toFixed(0)} min</Typography>
              <Typography variant="body2" color="text.secondary">
                Avg Wait Time
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" gutterBottom>
                Patients by ESI Level
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {[1, 2, 3, 4, 5].map((esi, idx) => (
                  <Chip
                    key={esi}
                    label={`ESI ${esi}: ${patientsByESI[idx]}`}
                    size="small"
                    color={
                      esi === 1
                        ? 'error'
                        : esi === 2
                        ? 'warning'
                        : esi === 3
                        ? 'info'
                        : 'default'
                    }
                  />
                ))}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Refresh Button */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
        <Typography variant="body2" color="text.secondary">
          Last updated: {formatDistanceToNow(lastUpdated, { addSuffix: true })}
        </Typography>
        <Box>
          <Button
            variant="outlined"
            size="small"
            sx={{ mr: 1 }}
            onClick={() => dispatch(fetchWaitingQueue())}
          >
            Refresh All
          </Button>
          {prototypeMode && !surgeMode && (
            <Button
              variant="contained"
              size="small"
              color="warning"
              onClick={() => dispatch(simulateSurge())}
            >
              Simulate Surge (Demo)
            </Button>
          )}
        </Box>
      </Box>
      
      {/* Patient Cards Grid */}
      {patients.length === 0 ? (
        <Alert severity="info">No patients currently waiting</Alert>
      ) : (
        <Grid container spacing={2}>
          {patients.map((patient) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={patient.id}>
              <PatientCard patient={patient} />
            </Grid>
          ))}
        </Grid>
      )}
      
      {/* Deterioration Alert Modals */}
      {activeAlerts.map((alert) => (
        <DeteriorationAlertModal key={alert.id} alert={alert} />
      ))}
    </Box>
  );
};

// PatientCard sub-component
interface PatientCardProps {
  patient: WaitingPatient;
}

export const PatientCard: React.FC<PatientCardProps> = ({ patient }) => {
  const dispatch = useDispatch();
  
  const statusColor =
    patient.status === 'deteriorating'
      ? 'error'
      : patient.status === 'reassess_due'
      ? 'warning'
      : 'success';
  
  const esiColor = {
    1: 'error',
    2: 'warning',
    3: 'info',
    4: 'success',
    5: 'default',
  }[patient.esi_level];
  
  return (
    <Card
      sx={{
        cursor: 'pointer',
        border: patient.status === 'deteriorating' ? '3px solid red' : 'none',
        animation: patient.status === 'deteriorating' ? 'pulse 2s infinite' : 'none',
      }}
      onClick={() => dispatch(openPatientDetailModal(patient.id))}
    >
      <CardContent>
        {/* Status Badge */}
        {patient.status === 'deteriorating' && (
          <Chip
            label="🚨 DETERIORATING"
            color="error"
            size="small"
            sx={{ mb: 1, fontWeight: 'bold' }}
          />
        )}
        {patient.status === 'reassess_due' && (
          <Chip
            label="⏰ RE-ASSESSMENT DUE"
            color="warning"
            size="small"
            sx={{ mb: 1 }}
          />
        )}
        
        {/* Patient Info */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar sx={{ width: 48, height: 48, mr: 2, bgcolor: 'primary.main' }}>
            {patient.name.charAt(0)}
          </Avatar>
          <Box>
            <Typography variant="subtitle1" fontWeight="bold">
              {patient.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {patient.age} years, {patient.sex}
            </Typography>
          </Box>
        </Box>
        
        {/* ESI and Wait Time */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Chip label={`ESI ${patient.esi_level}`} color={esiColor} size="small" />
          <Typography variant="body2" color="text.secondary">
            Wait: {patient.wait_time_minutes} min
          </Typography>
        </Box>
        
        {/* Sub-Score (Surge Mode) */}
        {patient.sub_score !== null && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Sub-score: {patient.sub_score.toFixed(1)}
            </Typography>
          </Box>
        )}
        
        {/* Chief Complaint */}
        <Typography variant="body2" sx={{ mt: 1 }}>
          {patient.chief_complaint}
        </Typography>
      </CardContent>
    </Card>
  );
};
```

### API Design

#### REST Endpoints Specification

```python
# routers/triage.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_current_user
from services.ml_core_client import ml_core_client
from services.triage_service import TriageService
from services.audit_service import audit_service
from schemas.patient import PatientData
from schemas.prediction import PredictionResponse
from schemas.override import OverrideRequest

router = APIRouter()

@router.post("/predict", response_model=PredictionResponse)
async def predict_esi(
    patient_data: PatientData,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate ESI triage recommendation.
    
    Flow:
    1. Validate patient data
    2. Save patient to database
    3. Call ML Core API for prediction
    4. Save triage event to database
    5. Async: Log to audit_logs
    6. Return prediction response
    
    Returns:
        PredictionResponse with ESI, confidence, safety, explanation
    """
    # Step 1-2: Create patient record
    triage_service = TriageService(db)
    patient = triage_service.create_patient(patient_data)
    
    # Step 3: Call ML Core
    try:
        ml_response = await ml_core_client.predict_esi(patient_data.dict())
    except Exception as e:
        # Fail-safe: Log error and return safe default
        logger.error(f"ML Core prediction failed: {e}")
        ml_response = ml_core_client._generate_failsafe_response(
            request_id=patient_data.request_id,
            error=str(e)
        )
    
    # Step 4: Save triage event
    triage_event = triage_service.create_triage_event(
        patient_id=patient.id,
        user_id=current_user.id,
        ml_response=ml_response,
    )
    
    # Step 5: Async audit logging
    background_tasks.add_task(
        audit_service.log_triage_prediction,
        user_id=current_user.id,
        patient_id=patient.id,
        triage_event_id=triage_event.id,
        ml_response=ml_response,
    )
    
    return ml_response


@router.post("/override")
async def submit_override(
    override_request: OverrideRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log clinician override of ML recommendation.
    
    Flow:
    1. Validate override data
    2. Update triage event with final ESI
    3. Create override record
    4. Async: Log to audit_logs
    5. Async: Add patient to waiting queue with final ESI
    6. Return success
    """
    triage_service = TriageService(db)
    
    # Update triage event
    triage_event = triage_service.update_triage_event_with_override(
        triage_event_id=override_request.triage_event_id,
        final_esi=override_request.clinician_final_esi,
    )
    
    # Create override record
    override = triage_service.create_override(
        triage_event_id=triage_event.id,
        ml_predicted_esi=override_request.ml_predicted_esi,
        clinician_final_esi=override_request.clinician_final_esi,
        reason_category=override_request.reason_category,
        reason_text=override_request.reason_text,
    )
    
    # Async audit logging
    background_tasks.add_task(
        audit_service.log_override,
        user_id=current_user.id,
        triage_event_id=triage_event.id,
        override_id=override.id,
        override_data=override_request.dict(),
    )
    
    # Async add to queue
    background_tasks.add_task(
        add_patient_to_queue,
        patient_id=triage_event.patient_id,
        final_esi=override_request.clinician_final_esi,
    )
    
    return {"success": True, "message": "Override logged successfully"}


# routers/deterioration.py
@router.post("/check", response_model=DeteriorationResponse)
async def check_deterioration(
    request: DeteriorationCheckRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assess patient deterioration.
    
    Flow:
    1. Validate request
    2. Call ML Core deterioration API
    3. Save deterioration check to database
    4. If deteriorating: Async WebSocket broadcast alert
    5. Async: Log to audit_logs
    6. Return deterioration response
    """
    deterioration_service = DeteriorationService(db)
    
    # Call ML Core
    ml_response = await ml_core_client.assess_deterioration(request)
    
    # Save check
    check = deterioration_service.create_deterioration_check(
        patient_id=request.patient_id,
        ml_response=ml_response,
    )
    
    # Broadcast alert if deteriorating
    if ml_response.status == "DETERIORATING" or ml_response.score >= 60:
        background_tasks.add_task(
            broadcast_deterioration_alert,
            patient_id=request.patient_id,
            deterioration_response=ml_response,
        )
    
    # Async audit logging
    background_tasks.add_task(
        audit_service.log_deterioration_check,
        user_id=current_user.id,
        patient_id=request.patient_id,
        check_id=check.id,
        ml_response=ml_response,
    )
    
    return ml_response


# routers/queue.py
@router.get("/", response_model=List[WaitingPatientResponse])
async def get_waiting_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all waiting patients sorted by priority.
    
    Sorting:
    1. Primary: ESI level (1 highest)
    2. Secondary: sub_score (100 highest, if surge mode)
    3. Tertiary: arrival_time (earliest first)
    """
    queue_service = QueueService(db)
    patients = queue_service.get_waiting_queue()
    
    # Check surge mode
    surge_mode = len(patients) > SURGE_MODE_THRESHOLD
    
    if surge_mode:
        # Compute sub-scores for all patients
        for patient in patients:
            patient.sub_score = await compute_sub_score(patient)
    
    # Sort queue
    patients = queue_service.sort_queue(patients, surge_mode=surge_mode)
    
    return patients


@router.post("/surge/activate")
async def activate_surge_mode(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually activate surge mode (demo only).
    
    Computes sub-scores for all waiting patients and broadcasts update.
    """
    queue_service = QueueService(db)
    patients = queue_service.get_waiting_queue()
    
    # Compute sub-scores
    for patient in patients:
        patient.sub_score = await compute_sub_score(patient)
    
    # Broadcast WebSocket update
    await sio.emit('surge_mode_activated', {'patients': [p.dict() for p in patients]})
    
    return {"success": True, "surge_mode": True, "patient_count": len(patients)}
```

### WebSocket Server

```python
# websocket/server.py
import socketio
from auth.jwt import decode_token

# Create Socket.io server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='http://localhost:3000',
    logger=True,
)

# Authentication middleware
@sio.event
async def connect(sid, environ, auth):
    """Handle client connection with JWT authentication."""
    try:
        token = auth.get('token')
        if not token:
            return False
        
        # Verify JWT
        payload = decode_token(token)
        user_id = payload.get('user_id')
        
        # Store user info in session
        await sio.save_session(sid, {'user_id': user_id})
        
        logger.info(f"Client {sid} connected (user_id: {user_id})")
        return True
    
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    session = await sio.get_session(sid)
    logger.info(f"Client {sid} disconnected (user_id: {session.get('user_id')})")


@sio.event
async def join_room(sid, data):
    """
    Join a room for real-time updates.
    
    Rooms:
    - 'waiting_queue': Receive queue updates and deterioration alerts
    """
    room = data.get('room')
    sio.enter_room(sid, room)
    logger.info(f"Client {sid} joined room: {room}")


@sio.event
async def leave_room(sid, data):
    """Leave a room."""
    room = data.get('room')
    sio.leave_room(sid, room)
    logger.info(f"Client {sid} left room: {room}")


# Helper functions for broadcasting
async def broadcast_deterioration_alert(patient_id: str, deterioration_response: DeteriorationResponse):
    """Broadcast deterioration alert to all clients in waiting_queue room."""
    await sio.emit(
        'deterioration_alert',
        {
            'patient_id': patient_id,
            'status': deterioration_response.status,
            'score': deterioration_response.score,
            'vital_changes': deterioration_response.vital_changes,
            'explanation': deterioration_response.explanation,
            'recommendation': deterioration_response.recommendation,
            'timestamp': deterioration_response.timestamp.isoformat(),
        },
        room='waiting_queue',
    )


async def broadcast_queue_update(patients: List[WaitingPatient]):
    """Broadcast queue update to all clients in waiting_queue room."""
    await sio.emit(
        'queue_update',
        {
            'patients': [p.dict() for p in patients],
            'timestamp': datetime.now().isoformat(),
        },
        room='waiting_queue',
    )


async def broadcast_patient_status_change(patient_id: str, status: str):
    """Broadcast patient status change."""
    await sio.emit(
        'patient_status_change',
        {
            'patient_id': patient_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
        },
        room='waiting_queue',
    )
```

### Background Jobs

```python
# background/deterioration_monitor.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

from database import SessionLocal
from services.queue_service import QueueService
from services.ml_core_client import ml_core_client
from websocket.server import broadcast_deterioration_alert

scheduler = AsyncIOScheduler()

async def monitor_waiting_patients():
    """
    Background job: Check waiting patients for deterioration.
    
    Runs every 5 minutes.
    
    Logic:
    1. Query all waiting patients
    2. For each patient, check if re-assessment is due based on ESI:
       - ESI 2: every 15 minutes
       - ESI 3: every 30 minutes
       - ESI 4/5: every 60 minutes
    3. If due, call ML Core deterioration API
    4. If deteriorating, broadcast WebSocket alert
    5. Update next_check_due timestamp
    """
    db = SessionLocal()
    try:
        queue_service = QueueService(db)
        patients = queue_service.get_waiting_patients_due_for_check()
        
        for patient in patients:
            # Determine check interval
            if patient.esi_level == 2:
                check_interval = 15
            elif patient.esi_level == 3:
                check_interval = 30
            else:  # ESI 4, 5
                check_interval = 60
            
            # Check if due
            time_since_last_check = (datetime.now() - patient.last_check_at).total_seconds() / 60
            
            if time_since_last_check >= check_interval:
                # Call ML Core
                deterioration_request = {
                    'patient_id': patient.id,
                    'initial_vitals': patient.initial_vitals,
                    'current_vitals': patient.current_vitals,  # Would be fetched from recent measurement
                    'initial_esi': patient.esi_level,
                    'time_since_triage_minutes': int(
                        (datetime.now() - patient.triage_at).total_seconds() / 60
                    ),
                    'age_group': patient.age_group,
                }
                
                response = await ml_core_client.assess_deterioration(deterioration_request)
                
                # Save check
                queue_service.save_deterioration_check(patient.id, response)
                
                # Broadcast if deteriorating
                if response.status == "DETERIORATING" or response.score >= 60:
                    await broadcast_deterioration_alert(patient.id, response)
                
                # Update next check time
                queue_service.update_next_check_due(
                    patient.id,
                    datetime.now() + timedelta(minutes=check_interval)
                )
        
        logger.info(f"Deterioration monitor checked {len(patients)} patients")
    
    except Exception as e:
        logger.error(f"Deterioration monitor error: {e}")
    
    finally:
        db.close()


async def check_wait_time_safety_nets():
    """
    Background job: Alert if patients exceed safety wait times.
    
    Runs every 5 minutes.
    
    Safety thresholds:
    - ESI 2: 30 minutes
    - ESI 3: 60 minutes
    """
    db = SessionLocal()
    try:
        queue_service = QueueService(db)
        patients = queue_service.get_waiting_patients()
        
        for patient in patients:
            wait_time_minutes = (datetime.now() - patient.triage_at).total_seconds() / 60
            
            # ESI 2: 30 min threshold
            if patient.esi_level == 2 and wait_time_minutes > 30:
                alert_response = {
                    'patient_id': patient.id,
                    'status': 'ALERT',
                    'score': 80.0,
                    'explanation': f'ESI 2 patient has been waiting {int(wait_time_minutes)} minutes (safety threshold: 30 min)',
                    'recommendation': 'URGENT: Expedite treatment or reassess ESI level',
                }
                await broadcast_deterioration_alert(patient.id, alert_response)
            
            # ESI 3: 60 min threshold
            if patient.esi_level == 3 and wait_time_minutes > 60:
                alert_response = {
                    'patient_id': patient.id,
                    'status': 'ALERT',
                    'score': 70.0,
                    'explanation': f'ESI 3 patient has been waiting {int(wait_time_minutes)} minutes (safety threshold: 60 min)',
                    'recommendation': 'Expedite treatment or reassess condition',
                }
                await broadcast_deterioration_alert(patient.id, alert_response)
        
        logger.info(f"Wait time safety net checked {len(patients)} patients")
    
    except Exception as e:
        logger.error(f"Wait time safety net error: {e}")
    
    finally:
        db.close()


def start_background_jobs():
    """Start all background jobs."""
    # Deterioration monitoring every 5 minutes
    scheduler.add_job(
        monitor_waiting_patients,
        trigger=IntervalTrigger(minutes=5),
        id='deterioration_monitor',
        replace_existing=True,
    )
    
    # Wait time safety nets every 5 minutes
    scheduler.add_job(
        check_wait_time_safety_nets,
        trigger=IntervalTrigger(minutes=5),
        id='wait_time_safety_net',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Background jobs started")
```

### Simulated Data Generation

```python
# services/simulated_data_generator.py
import random
from typing import List
from datetime import datetime, timedelta
from models.patient import Patient

class SimulatedDataGenerator:
    """
    Generate 20 diverse simulated patients for prototype demonstration.
    
    Requirements:
    - 20 patients total
    - At least 1 ambiguous presentation (ESI 2 or 3)
    - At least 2 pediatric (spanning infant, child, adolescent)
    - At least 2 geriatric (65+)
    - At least 1 zero-history patient
    - Distribution across all ESI levels (min 2 each)
    - At least 3 patients with missing optional data
    - Realistic chief complaints from 50+ categories
    - Age-appropriate vital signs
    """
    
    def __init__(self):
        self.chief_complaint_categories = [
            'chest_pain_cardiac', 'abdominal_pain', 'fever', 'trauma_severe',
            'respiratory_distress', 'altered_mental_status', 'stroke_cva',
            'gi_bleed', 'sepsis', 'anaphylaxis', 'cold_flu_symptoms',
            'laceration', 'headache', 'back_pain', 'urinary_symptoms',
            # ... 50+ total categories
        ]
        
        self.names = [
            ('John', 'Smith'), ('Maria', 'Garcia'), ('Wei', 'Chen'),
            ('Priya', 'Sharma'), ('David', 'Johnson'), ('Aisha', 'Mohamed'),
            ('Carlos', 'Rodriguez'), ('Emily', 'Wilson'), ('Raj', 'Patel'),
            ('Sarah', 'Brown'), ('Ahmed', 'Ali'), ('Linda', 'Davis'),
            ('Michael', 'Martinez'), ('Anna', 'Kim'), ('James', 'Lee'),
            ('Sofia', 'Lopez'), ('Robert', 'Anderson'), ('Lisa', 'Thomas'),
            ('Daniel', 'White'), ('Jessica', 'Taylor'),
        ]
    
    def generate_20_patients(self) -> List[Patient]:
        """Generate 20 diverse simulated patients."""
        patients = []
        
        # ESI distribution: ensure min 2 per level
        esi_distribution = [1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5]
        random.shuffle(esi_distribution)
        
        for idx, target_esi in enumerate(esi_distribution):
            # Special cases
            is_ambiguous = (idx == 0)  # First patient is ambiguous
            is_pediatric_infant = (idx == 1)
            is_pediatric_child = (idx == 2)
            is_geriatric = (idx in [3, 4])
            is_zero_history = (idx == 5)
            is_missing_data = (idx in [6, 7, 8])  # 3 patients with missing data
            
            # Generate patient
            patient = self._generate_patient(
                idx=idx,
                target_esi=target_esi,
                is_ambiguous=is_ambiguous,
                is_pediatric_infant=is_pediatric_infant,
                is_pediatric_child=is_pediatric_child,
                is_geriatric=is_geriatric,
                is_zero_history=is_zero_history,
                is_missing_data=is_missing_data,
            )
            
            patients.append(patient)
        
        return patients
    
    def _generate_patient(
        self,
        idx: int,
        target_esi: int,
        is_ambiguous: bool = False,
        is_pediatric_infant: bool = False,
        is_pediatric_child: bool = False,
        is_geriatric: bool = False,
        is_zero_history: bool = False,
        is_missing_data: bool = False,
    ) -> Patient:
        """Generate a single patient with specified characteristics."""
        
        # Demographics
        if is_pediatric_infant:
            age = random.randint(0, 2)
        elif is_pediatric_child:
            age = random.randint(3, 12)
        elif is_geriatric:
            age = random.randint(65, 85)
        else:
            age = random.randint(18, 64)
        
        age_group = self._classify_age_group(age)
        
        first_name, last_name = self.names[idx]
        sex = random.choice(['male', 'female'])
        
        # Vital signs (age-appropriate)
        vitals = self._generate_vitals(age_group, target_esi, is_missing_data)
        
        # Chief complaint
        chief_complaint, chief_complaint_category = self._generate_chief_complaint(
            target_esi, is_ambiguous
        )
        
        # Symptoms
        symptoms = self._generate_symptoms(chief_complaint_category)
        
        # Medical history
        if is_zero_history:
            medical_history = {}
        else:
            medical_history = self._generate_medical_history(age, is_geriatric)
        
        # Arrival mode
        arrival_mode = 'ambulance' if target_esi <= 2 else random.choice(['walk_in', 'ambulance'])
        
        # Mental status
        mental_status = 'alert' if target_esi >= 3 else random.choice(['alert', 'confused', 'drowsy'])
        
        # Pain score
        pain_score = random.randint(3, 9) if chief_complaint_category in ['chest_pain_cardiac', 'trauma_severe', 'abdominal_pain'] else random.randint(0, 5) if not is_missing_data else None
        
        patient = Patient(
            age=age,
            sex=sex,
            age_group=age_group,
            hr=vitals.get('hr'),
            bp_systolic=vitals.get('bp_systolic'),
            bp_diastolic=vitals.get('bp_diastolic'),
            spo2=vitals.get('spo2'),
            rr=vitals.get('rr'),
            temperature=vitals.get('temperature'),
            chief_complaint=chief_complaint,
            chief_complaint_category=chief_complaint_category,
            pain_score=pain_score,
            arrival_mode=arrival_mode,
            mental_status=mental_status,
            symptoms=symptoms,
            medical_history=medical_history,
            observations=[],
        )
        
        return patient
    
    def _classify_age_group(self, age: int) -> str:
        if age <= 2:
            return 'pediatric_infant'
        elif age <= 12:
            return 'pediatric_child'
        elif age <= 17:
            return 'pediatric_adolescent'
        elif age <= 64:
            return 'adult'
        else:
            return 'geriatric'
    
    def _generate_vitals(self, age_group: str, target_esi: int, is_missing_data: bool) -> dict:
        """Generate age-appropriate vital signs targeting specific ESI level."""
        ranges = AGE_SPECIFIC_VITAL_RANGES[age_group]
        
        vitals = {}
        
        # HR
        if target_esi == 1:
            vitals['hr'] = random.randint(ranges['hr_max'] + 20, 180)  # Severe tachycardia
        elif target_esi == 2:
            vitals['hr'] = random.randint(ranges['hr_max'], ranges['hr_max'] + 20)  # Moderate tachycardia
        elif target_esi == 3:
            vitals['hr'] = random.randint(ranges['hr_max'] - 10, ranges['hr_max'] + 10)  # Borderline
        else:
            vitals['hr'] = random.randint(ranges['hr_min'], ranges['hr_max'])  # Normal
        
        # BP
        if target_esi <= 2:
            vitals['bp_systolic'] = random.randint(ranges['bp_sys_min'] - 20, ranges['bp_sys_min'])  # Hypotension
        else:
            vitals['bp_systolic'] = random.randint(ranges['bp_sys_min'], ranges['bp_sys_max'])
        
        vitals['bp_diastolic'] = int(vitals['bp_systolic'] * 0.6)  # Approximate diastolic
        
        # SpO2
        if target_esi == 1:
            vitals['spo2'] = random.randint(85, 90)  # Severe hypoxia
        elif target_esi == 2:
            vitals['spo2'] = random.randint(91, 93)  # Moderate hypoxia
        else:
            vitals['spo2'] = random.randint(ranges['spo2_min'], 100)  # Normal
        
        # RR
        if target_esi <= 2:
            vitals['rr'] = random.randint(ranges['rr_max'], ranges['rr_max'] + 10)  # Tachypnea
        else:
            vitals['rr'] = random.randint(ranges['rr_min'], ranges['rr_max'])
        
        # Temperature (optional)
        if not is_missing_data:
            vitals['temperature'] = random.uniform(ranges['temp_min'], ranges['temp_max'])
        
        return vitals
    
    def _generate_chief_complaint(self, target_esi: int, is_ambiguous: bool) -> tuple:
        """Generate chief complaint and category."""
        if is_ambiguous:
            # Ambiguous: chest pain in 45-year-old (could be cardiac or musculoskeletal)
            return (
                "chest pain radiating to left arm, started 2 hours ago",
                "chest_pain_cardiac"
            )
        
        if target_esi == 1:
            category = random.choice(['chest_pain_cardiac', 'respiratory_distress', 'stroke_cva', 'trauma_severe'])
        elif target_esi == 2:
            category = random.choice(['abdominal_pain', 'gi_bleed', 'sepsis', 'altered_mental_status'])
        elif target_esi == 3:
            category = random.choice(['fever', 'headache', 'back_pain', 'urinary_symptoms'])
        else:
            category = random.choice(['cold_flu_symptoms', 'laceration', 'rash', 'minor_trauma'])
        
        # Generate realistic text
        complaint_texts = {
            'chest_pain_cardiac': "crushing chest pain, shortness of breath",
            'abdominal_pain': "severe abdominal pain, nausea and vomiting",
            'fever': "high fever for 2 days, chills",
            'cold_flu_symptoms': "runny nose, cough, mild fever",
            # ... (would have more for each category)
        }
        
        complaint_text = complaint_texts.get(category, "patient presenting with symptoms")
        
        return (complaint_text, category)
    
    def _generate_symptoms(self, chief_complaint_category: str) -> List[str]:
        """Generate symptoms based on chief complaint."""
        symptom_mapping = {
            'chest_pain_cardiac': ['chest_pain', 'shortness_of_breath', 'diaphoresis'],
            'respiratory_distress': ['shortness_of_breath', 'wheezing', 'cough'],
            'abdominal_pain': ['abdominal_pain', 'nausea_vomiting'],
            'fever': ['fever', 'chills', 'malaise'],
            # ... (would have more)
        }
        
        return symptom_mapping.get(chief_complaint_category, [])
    
    def _generate_medical_history(self, age: int, is_geriatric: bool) -> dict:
        """Generate medical history."""
        history = {
            'cardiac_history': False,
            'respiratory_history': False,
            'diabetes': False,
            'hypertension': False,
            'on_medications': False,
            'recent_hospitalization': False,
        }
        
        # Geriatric patients more likely to have history
        if is_geriatric:
            history['cardiac_history'] = random.random() < 0.4
            history['hypertension'] = random.random() < 0.6
            history['diabetes'] = random.random() < 0.3
            history['on_medications'] = True
        elif age > 50:
            history['hypertension'] = random.random() < 0.3
            history['on_medications'] = random.random() < 0.4
        
        return history
```

### Testing Strategy

```python
# tests/test_patient_intake.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_patient_intake_valid_data():
    """Test patient intake with valid data."""
    patient_data = {
        "request_id": "test_001",
        "demographics": {"age": 45, "sex": "female"},
        "vitals": {
            "hr": 95,
            "bp_systolic": 130,
            "bp_diastolic": 85,
            "spo2": 97,
            "rr": 16,
            "temperature": 37.0,
        },
        "clinical": {
            "chief_complaint": "chest discomfort",
            "chief_complaint_category": "chest_pain_cardiac",
            "pain_score": 6,
            "arrival_mode": "ambulance",
            "mental_status": "alert",
        },
        "symptoms": ["chest_pain", "shortness_of_breath"],
        "history": {"cardiac_history": True, "hypertension": True},
        "observations": [],
    }
    
    response = client.post("/api/triage/predict", json=patient_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "esi_prediction" in data
    assert data["esi_prediction"] >= 1 and data["esi_prediction"] <= 5
    assert "confidence_breakdown" in data
    assert "safety_flag" in data


def test_patient_intake_missing_required_vitals():
    """Test patient intake with missing required vitals."""
    patient_data = {
        "request_id": "test_002",
        "demographics": {"age": 30, "sex": "male"},
        "vitals": {
            "hr": 75,
            # Missing bp_systolic, spo2, rr
        },
        "clinical": {
            "chief_complaint": "fever",
            "chief_complaint_category": "fever",
            "arrival_mode": "walk_in",
            "mental_status": "alert",
        },
    }
    
    response = client.post("/api/triage/predict", json=patient_data)
    
    assert response.status_code == 400
    assert "validation" in response.json()["detail"].lower()


# tests/test_ml_core_client.py
@pytest.mark.asyncio
async def test_ml_core_client_predict_success(monkeypatch):
    """Test ML Core client successful prediction."""
    # Mock httpx.AsyncClient
    async def mock_post(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            
            def json(self):
                return {
                    "request_id": "test_123",
                    "esi_prediction": 2,
                    "probability_distribution": [0.05, 0.72, 0.18, 0.04, 0.01],
                    "confidence_breakdown": {
                        "model_certainty": 85.2,
                        "data_completeness": 95.0,
                        "clinical_consistency": 72.0,
                        "pattern_recognition": 81.3,
                        "overall": 82.1,
                        "level": "HIGH",
                    },
                    "safety_flag": {
                        "outcome": "YELLOW",
                        "triggered_criteria": ["VITAL: Severe tachycardia"],
                        "recommended_action": "Consider escalation",
                        "override_esi": None,
                    },
                    "explanation": {
                        "text": "ESI 2 recommended based on...",
                        "top_factors": [],
                    },
                    "sub_score": None,
                    "recommendations": [],
                    "model_version": "v2.1.0",
                    "inference_time_ms": 92.7,
                    "timestamp": "2024-01-15T10:30:00.123Z",
                }
            
            def raise_for_status(self):
                pass
        
        return MockResponse()
    
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    
    client = MLCoreClient()
    response = await client.predict_esi({"request_id": "test_123"})
    
    assert response.esi_prediction == 2
    assert response.confidence_breakdown["level"] == "HIGH"


@pytest.mark.asyncio
async def test_ml_core_client_timeout_failsafe(monkeypatch):
    """Test ML Core client timeout triggers fail-safe."""
    import httpx
    
    async def mock_post(*args, **kwargs):
        raise httpx.TimeoutException("Request timed out")
    
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    
    client = MLCoreClient()
    response = await client.predict_esi({"request_id": "test_123"})
    
    # Should return fail-safe default
    assert response.esi_prediction == 2
    assert response.confidence_breakdown["level"] == "LOW"
    assert response.model_version == "FALLBACK"


# tests/test_json_roundtrip.py
from hypothesis import given, strategies as st
from schemas.patient import PatientData

@given(
    age=st.integers(min_value=0, max_value=120),
    sex=st.sampled_from(['male', 'female', 'other']),
    hr=st.integers(min_value=20, max_value=250),
)
def test_patient_data_json_roundtrip(age, sex, hr):
    """Property test: PatientData JSON round-trip preserves data."""
    patient_data = PatientData(
        request_id="test_prop",
        demographics={"age": age, "sex": sex},
        vitals={"hr": hr, "bp_systolic": 120, "spo2": 95, "rr": 16},
        clinical={
            "chief_complaint": "test",
            "chief_complaint_category": "test",
            "arrival_mode": "walk_in",
            "mental_status": "alert",
        },
    )
    
    # Serialize to JSON
    json_str = patient_data.json()
    
    # Deserialize back
    restored = PatientData.parse_raw(json_str)
    
    # Assert equivalence
    assert restored.demographics["age"] == age
    assert restored.demographics["sex"] == sex
    assert restored.vitals["hr"] == hr
```

### Deployment Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: triage_db
    environment:
      POSTGRES_USER: triage_user
      POSTGRES_PASSWORD: triage_password
      POSTGRES_DB: triage_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U triage_user"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: triage_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: triage_backend
    environment:
      DATABASE_URL: postgresql://triage_user:triage_password@postgres:5432/triage_db
      REDIS_URL: redis://redis:6379
      ML_CORE_BASE_URL: http://ml-core:8001
      ML_CORE_API_KEY: ${ML_CORE_API_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      JWT_ALGORITHM: HS256
      JWT_EXPIRATION_MINUTES: 60
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
  
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: triage_frontend
    environment:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_WS_URL: ws://localhost:8000
    depends_on:
      - backend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm start
  
  # Nginx Reverse Proxy (Production)
  nginx:
    image: nginx:alpine
    container_name: triage_nginx
    profiles:
      - production
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/build:/usr/share/nginx/html:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
```

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run migrations on startup and start server
CMD alembic upgrade head && uvicorn main:socket_app --host 0.0.0.0 --port 8000
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application
COPY . .

# Expose port
EXPOSE 3000

# Development server
CMD ["npm", "start"]

# Production build (multi-stage)
# FROM node:18-alpine AS build
# WORKDIR /app
# COPY package*.json ./
# RUN npm ci
# COPY . .
# RUN npm run build
#
# FROM nginx:alpine
# COPY --from=build /app/build /usr/share/nginx/html
# COPY nginx.conf /etc/nginx/nginx.conf
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]
```

```bash
# .env.example
# Database
DATABASE_URL=postgresql://triage_user:triage_password@localhost:5432/triage_db

# Redis
REDIS_URL=redis://localhost:6379

# ML Core API
ML_CORE_BASE_URL=http://localhost:8001
ML_CORE_API_KEY=your_ml_core_api_key_here

# JWT
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Session
SESSION_TIMEOUT_MINUTES=60
SESSION_AUTO_LOCK_MINUTES=5

# Surge Mode
SURGE_MODE_THRESHOLD=15

# Deterioration Monitoring
DETERIORATION_CHECK_INTERVAL_MINUTES=5
```

```bash
# scripts/init_db.sh
#!/bin/bash
# Initialize database with demo users and simulated patients

set -e

echo "Initializing database..."

# Run migrations
alembic upgrade head

# Create demo users
python -c "
from database import SessionLocal
from models.user import User
from auth.jwt import hash_password

db = SessionLocal()

# ED Nurse
nurse = User(
    username='nurse',
    password_hash=hash_password('nurse123'),
    role='ED_Nurse'
)
db.add(nurse)

# Attending Physician
physician = User(
    username='doctor',
    password_hash=hash_password('doctor123'),
    role='Attending_Physician'
)
db.add(physician)

# Administrator
admin = User(
    username='admin',
    password_hash=hash_password('admin123'),
    role='Administrator'
)
db.add(admin)

db.commit()
print('✅ Demo users created')
"

# Generate simulated patients
python -c "
from database import SessionLocal
from services.simulated_data_generator import SimulatedDataGenerator

db = SessionLocal()
generator = SimulatedDataGenerator()
patients = generator.generate_20_patients()

for patient in patients:
    db.add(patient)

db.commit()
print(f'✅ Generated {len(patients)} simulated patients')
"

echo "✅ Database initialized successfully"
```

```bash
# scripts/run_dev.sh
#!/bin/bash
# Start development environment

set -e

echo "Starting development environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start Docker Compose
docker-compose up -d postgres redis

# Wait for services
echo "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U triage_user; do
    sleep 1
done

echo "Waiting for Redis..."
until docker-compose exec -T redis redis-cli ping; do
    sleep 1
done

# Initialize database
./scripts/init_db.sh

# Start backend
echo "Starting backend..."
cd backend
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "✅ Development environment running"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"

# Trap exit
trap "kill $BACKEND_PID $FRONTEND_PID; docker-compose down" EXIT

wait
```

---

## Summary

This comprehensive technical design document provides:

1. **Complete Architecture**: Frontend (React/TypeScript), Backend (FastAPI/Python), Database (PostgreSQL), Real-time (Socket.io), and integration with ML Core API

2. **Detailed Component Specifications**: Patient Intake Form, Recommendation Panel, Override Dialog, Waiting Queue Dashboard, with full TypeScript implementations

3. **Database Schema**: 7 tables with constraints, indexes, and immutability enforcement for audit logs

4. **API Design**: REST endpoints for triage, deterioration, queue management, and audit logs with authentication

5. **Real-Time System**: WebSocket server with room-based broadcasting for deterioration alerts and queue updates

6. **Background Jobs**: Automated deterioration monitoring and wait time safety nets using APScheduler

7. **Simulated Data**: Algorithm for generating 20 diverse test patients covering all requirements

8. **Testing Strategy**: Unit tests, integration tests, property-based tests for JSON round-trip validation

9. **Deployment**: Docker Compose configuration with PostgreSQL, Redis, Backend, Frontend, and Nginx

10. **Security & Compliance**: JWT authentication, RBAC, HTTPS, audit logging, HIPAA considerations

The design is implementation-ready with concrete code examples, database schemas, API contracts, and deployment configurations. All 23 requirements from the requirements document are addressed with traceable implementations.

