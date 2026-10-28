import { Component, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { CryptoService, WrongPasswordError } from '../core/crypto.service';
import { FileMeta, FilesService } from '../core/files.service';

@Component({
  selector: 'app-files',
  standalone: true,
  imports: [FormsModule, DatePipe],
  template: `
    <section class="card">
      <h2>Upload a file</h2>
      <p class="sub">Pick a file and a password. The file is encrypted here, in your browser, before upload.
        If you lose the password, nobody can recover the file — including us.</p>
      <div class="grid">
        <div>
          <label for="file">File</label>
          <input id="file" type="file" (change)="onPick($event)" />
        </div>
        <div>
          <label for="enc-password">Encryption password</label>
          <input id="enc-password" type="password" [(ngModel)]="uploadPassword" autocomplete="new-password" />
        </div>
      </div>
      @if (uploadError) { <div class="banner-error" id="upload-error">{{ uploadError }}</div> }
      @if (uploadOk) { <div class="banner-ok" id="upload-ok">{{ uploadOk }}</div> }
      <button class="primary" id="upload" (click)="upload()" [disabled]="uploading">
        {{ uploading ? 'Encrypting & uploading…' : 'Encrypt & upload' }}
      </button>
    </section>

    <section class="card">
      <h2>Your files</h2>
      @if (listNotice) { <div class="banner-ok" id="delete-ok">{{ listNotice }}</div> }
      @if (loading) {
        <p class="sub">Loading…</p>
      } @else if (files.length === 0) {
        <p class="empty" id="empty-state">You haven't uploaded any files yet.</p>
      } @else {
        <ul class="files" id="file-list">
          @for (f of files; track f.hash) {
            <li>
              <div class="meta">
                <strong>{{ f.filename }}</strong>
                <span>{{ f.uploaded_at | date: 'MMM d, y, h:mm a' }}</span>
              </div>
              @if (confirmingDelete === f.hash) {
                <div class="confirm" id="delete-confirm">
                  <span>Delete <strong>{{ f.filename }}</strong> permanently? This can't be undone.</span>
                  <div class="confirm-actions">
                    <button class="danger" id="delete-yes" (click)="confirmDelete(f)" [disabled]="busy">{{ busy ? 'Deleting…' : 'Delete permanently' }}</button>
                    <button id="delete-no" (click)="cancelDelete()">Keep file</button>
                  </div>
                </div>
                @if (deleteError) { <div class="field-error dl-error">{{ deleteError }}</div> }
              } @else if (decrypting === f.hash) {
                <div class="dl">
                  <input type="password" placeholder="Password for this file" [(ngModel)]="downloadPassword"
                         (keyup.enter)="decrypt(f)" class="dl-pw" />
                  <button class="primary" (click)="decrypt(f)" [disabled]="busy">{{ busy ? 'Decrypting…' : 'Decrypt & download' }}</button>
                  <button (click)="cancel()">Cancel</button>
                </div>
                @if (downloadError) { <div class="field-error dl-error">{{ downloadError }}</div> }
              } @else {
                <div class="actions">
                  <button class="open" (click)="startDecrypt(f)">Decrypt</button>
                  <button class="delete-btn" (click)="askDelete(f)">Delete</button>
                </div>
              }
            </li>
          }
        </ul>
      }
    </section>
  `,
  styles: [`
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 26px; margin-bottom: 22px; }
    h2 { font-size: 20px; }
    .sub { color: var(--muted); font-size: 14px; margin: 8px 0 18px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
    input[type=file] { color: var(--muted); font-size: 14px; }
    .banner-error, .banner-ok { margin-bottom: 14px; }
    .empty { color: var(--muted); padding: 18px 0 4px; }
    .files { list-style: none; padding: 0; margin: 14px 0 0; }
    .files li { display: grid; grid-template-columns: 1fr auto; gap: 8px 16px; align-items: center; padding: 14px 0; border-top: 1px solid var(--border); }
    .meta { display: flex; flex-direction: column; }
    .meta span { color: var(--muted); font-size: 13px; }
    .dl { display: flex; gap: 8px; grid-column: 1 / -1; }
    .dl-pw { flex: 1; }
    .dl-error { grid-column: 1 / -1; margin-top: 0; }
    .actions { display: flex; gap: 8px; }
    .delete-btn { color: var(--danger); }
    .confirm { grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
      background: rgba(255,107,107,.06); border: 1px solid rgba(255,107,107,.35); border-radius: 8px; padding: 12px 14px; font-size: 14px; }
    .confirm-actions { display: flex; gap: 8px; }
    button.danger { background: var(--danger); color: #1a0505; border-color: var(--danger); font-weight: 600; }
  `],
})
export class FilesComponent implements OnInit {
  private filesApi = inject(FilesService);
  private crypto = inject(CryptoService);

  files: FileMeta[] = [];
  loading = true;

  picked: File | null = null;
  uploadPassword = '';
  uploading = false;
  uploadError = '';
  uploadOk = '';

  decrypting: string | null = null;
  downloadPassword = '';
  downloadError = '';
  busy = false;

  confirmingDelete: string | null = null;
  deleteError = '';
  listNotice = '';

  async ngOnInit() {
    await this.refresh();
  }

  async refresh() {
    this.loading = true;
    try {
      this.files = await this.filesApi.list();
    } finally {
      this.loading = false;
    }
  }

  onPick(ev: Event) {
    this.picked = (ev.target as HTMLInputElement).files?.[0] ?? null;
  }

  async upload() {
    this.uploadError = '';
    this.uploadOk = '';
    if (!this.picked) { this.uploadError = 'Choose a file to upload first.'; return; }
    if (!this.uploadPassword) { this.uploadError = 'Enter an encryption password. Without one, the file can\'t be protected.'; return; }
    this.uploading = true;
    try {
      const cipher = await this.crypto.encrypt(await this.picked.arrayBuffer(), this.uploadPassword);
      await this.filesApi.upload(cipher, this.picked.name);
      this.uploadOk = `Uploaded "${this.picked.name}" — encrypted before it left your browser.`;
      this.uploadPassword = '';
      await this.refresh();
    } catch (err) {
      const e = err as HttpErrorResponse;
      this.uploadError = e.error?.detail ?? "Upload failed. Nothing was saved — please try again.";
    } finally {
      this.uploading = false;
    }
  }

  startDecrypt(f: FileMeta) {
    this.confirmingDelete = null;
    this.listNotice = '';
    this.decrypting = f.hash;
    this.downloadPassword = '';
    this.downloadError = '';
  }

  cancel() {
    this.decrypting = null;
    this.downloadError = '';
  }

  async decrypt(f: FileMeta) {
    this.downloadError = '';
    if (!this.downloadPassword) { this.downloadError = 'Enter the password used to encrypt this file.'; return; }
    this.busy = true;
    try {
      const blob = await this.filesApi.download(f.hash);
      const plain = await this.crypto.decrypt(blob, this.downloadPassword);
      const url = URL.createObjectURL(new Blob([plain]));
      const a = document.createElement('a');
      a.href = url;
      a.download = f.filename;
      a.click();
      URL.revokeObjectURL(url);
      this.cancel();
    } catch (err) {
      this.downloadError = err instanceof WrongPasswordError ? err.message : "Couldn't download this file. Please try again.";
    } finally {
      this.busy = false;
    }
  }

  askDelete(f: FileMeta) {
    this.decrypting = null;
    this.listNotice = '';
    this.deleteError = '';
    this.confirmingDelete = f.hash;
  }

  cancelDelete() {
    this.confirmingDelete = null;
    this.deleteError = '';
  }

  async confirmDelete(f: FileMeta) {
    this.busy = true;
    this.deleteError = '';
    try {
      await this.filesApi.delete(f.hash);
      this.confirmingDelete = null;
      this.listNotice = `Deleted "${f.filename}".`;
      await this.refresh();
    } catch (err) {
      const e = err as HttpErrorResponse;
      this.deleteError = e.status === 404 ? 'That file no longer exists.' : "Couldn't delete this file. Nothing was removed — please try again.";
      if (e.status === 404) await this.refresh();
    } finally {
      this.busy = false;
    }
  }
}
