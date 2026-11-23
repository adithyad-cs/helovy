import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { DashboardPage } from '../features/dashboard/DashboardPage'
import { LoginPage } from '../features/auth/LoginPage'
import { AppShell } from './AppShell'
import { NotBuiltYetPage } from './NotBuiltYetPage'
import { NotFoundPage } from './NotFoundPage'
import { RequireAuth } from './RequireAuth'
import { SkeletonPage } from './SkeletonPage'

// Routes of docs/08 §12.1. Sections not built yet render an honest placeholder.
const router = createBrowserRouter([
  { path: '/', element: <SkeletonPage /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/app',
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'business', element: <NotBuiltYetPage title="Business profile" /> },
          { path: 'customers/*', element: <NotBuiltYetPage title="Customers" /> },
          { path: 'invoices/*', element: <NotBuiltYetPage title="Invoices" /> },
          { path: 'templates', element: <NotBuiltYetPage title="Templates" /> },
          { path: '*', element: <NotFoundPage inShell /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
