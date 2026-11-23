import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { LoginPage } from '../features/auth/LoginPage'
import { BusinessProfilePage } from '../features/business/BusinessProfilePage'
import { CustomerFormPage } from '../features/customers/CustomerFormPage'
import { CustomerListPage } from '../features/customers/CustomerListPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { InvoicePage } from '../features/invoices/InvoicePage'
import { InvoicesIndexPage } from '../features/invoices/InvoicesIndexPage'
import { NewInvoicePage } from '../features/invoices/NewInvoicePage'
import { TemplatesPage } from '../features/templates/TemplatesPage'
import { AppShell } from './AppShell'
import { NotFoundPage } from './NotFoundPage'
import { RequireAuth } from './RequireAuth'
import { RequireBusiness } from './RequireBusiness'
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
          { path: 'business', element: <BusinessProfilePage /> },
          {
            element: <RequireBusiness />,
            children: [
              { path: 'customers', element: <CustomerListPage /> },
              { path: 'customers/new', element: <CustomerFormPage /> },
              { path: 'customers/:customerId', element: <CustomerFormPage /> },
              { path: 'invoices', element: <InvoicesIndexPage /> },
              { path: 'invoices/new', element: <NewInvoicePage /> },
              { path: 'invoices/:documentId', element: <InvoicePage /> },
            ],
          },
          { path: 'templates', element: <TemplatesPage /> },
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
