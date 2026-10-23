import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { FilesComponent } from './files/files.component';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', component: FilesComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: '' },
];
