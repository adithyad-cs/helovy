import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { NotFoundPage } from './NotFoundPage'
import { SkeletonPage } from './SkeletonPage'

// M0 skeleton routes. M1 adds /login, the /app shell and the route guard (docs/08 §12.1);
// M7 replaces the skeleton page with the landing page (docs/08 §10).
const router = createBrowserRouter([
  { path: '/', element: <SkeletonPage /> },
  { path: '*', element: <NotFoundPage /> },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
