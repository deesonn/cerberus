import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/**
 * If the server says our session is no longer valid (expired, or logged out elsewhere),
 * clear the local token and send the user to the login page instead of leaving them on a
 * screen where every action silently fails.
 */
export const sessionInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const isAuthCall = req.url.includes('/auth/');
      if (err.status === 401 && !isAuthCall && auth.loggedIn) {
        const expired = err.error?.detail === 'Session expired';
        auth.clear();
        router.navigate(['/login'], { queryParams: { reason: expired ? 'expired' : 'signin' } });
      }
      return throwError(() => err);
    }),
  );
};
