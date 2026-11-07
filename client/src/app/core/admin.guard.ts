import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/** Not logged in -> /login. Logged in but not an administrator -> back to the file list. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.loggedIn) return router.createUrlTree(['/login']);
  return auth.isAdmin ? true : router.createUrlTree(['/']);
};
