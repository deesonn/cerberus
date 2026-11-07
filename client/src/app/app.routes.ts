import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { FilesComponent } from './files/files.component';
import { AccountComponent } from './account/account.component';
import { AdminComponent } from './admin/admin.component';
import { authGuard } from './core/auth.guard';
import { adminGuard } from './core/admin.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', component: FilesComponent, canActivate: [authGuard] },
  { path: 'account', component: AccountComponent, canActivate: [authGuard] },
  { path: 'admin', component: AdminComponent, canActivate: [adminGuard] },
  { path: '**', redirectTo: '' },
];
