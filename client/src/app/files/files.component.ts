import { Component, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { CryptoService, WrongPasswordError } from '../core/crypto.service';
import { FileMeta, FilesService, StorageInfo } from '../core/files.service';
import { SortKey, cleanFilename, filterFiles, formatBytes, percentUsed, sortFiles } from '../core/file-list';

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
      @if (storage) {
        <div class="usage" id="usage">
          <div class="usage-text">
            <span id="usage-label">{{ fmt(storage.used_bytes) }} of {{ fmt(storage.quota_bytes) }} used</span>
            <span>Max {{ fmt(storage.max_upload_bytes) }} per file</span>
          </div>
          <div class="bar" role="progressbar" [attr.aria-valuenow]="pct" aria-valuemin="0" aria-valuemax="100">
            <div class="fill" [class.warn]="pct >= 90" [style.width.%]="pct"></div>
          </div>
        </div>
      }
      @if (uploadError) { <div class="banner-error" id="upload-error">{{ uploadError }}</div> }
      @if (uploadOk) { <div class="banner-ok" id="upload-ok">{{ uploadOk }}</div> }
      <button class="primary" id="upload" (click)="upload()" [disabled]="uploading">
        {{ uploading ? 'Encrypting & uploading…' : 'Encrypt & upload' }}
      </button>
    </section>

    <section class="card">
      <h2>Your files</h2>
      @if (listNotice) { <div class="banner-ok" id="delete-ok">{{ listNotice }}</div> }
      @if (renameNotice) { <div class="banner-ok" id="rename-ok">{{ renameNotice }}</div> }
      @if (loading) {
        <p class="sub">Loading…</p>
      } @else if (files.length === 0) {
        <p class="empty" id="empty-state">You haven't uploaded any files yet.</p>
      } @else {
        <div class="tools">
          <input id="search" type="search" placeholder="Search your files" [(ngModel)]="search" aria-label="Search your files" />
          <select id="sort" [(ngModel)]="sortKey" aria-label="Sort files">
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="name">Name A–Z</option>
            <option value="size">Largest first</option>
          </select>
        </div>
        <p class="sub count" id="count">{{ visible.length }} of {{ files.length }} file{{ files.length === 1 ? '' : 's' }}</p>
        @if (visible.length === 0) {
          <p class="empty" id="no-matches">No files match "{{ search }}".</p>
        }
        <ul class="files" id="file-list">
          @for (f of visible; track f.hash) {
            <li>
              <div class="meta">
                <strong>{{ f.filename }}</strong>
                <span>{{ fmt(f.size) }} · {{ f.uploaded_at | date: 'MMM d, y, h:mm a' }}</span>
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
              } @else if (renaming === f.hash) {
                <div class="dl">
                  <input type="text" id="rename-input" [(ngModel)]="renameValue" maxlength="255" aria-label="New file name"
                         (keyup.enter)="saveRename(f)" (keyup.escape)="cancelRename()" class="dl-pw" />
                  <button class="primary" id="rename-save" (click)="saveRename(f)" [disabled]="busy">{{ busy ? 'Saving…' : 'Save name' }}</button>
                  <button id="rename-cancel" (click)="cancelRename()">Cancel</button>
                </div>
                @if (renameError) { <div class="field-error dl-error" id="rename-error">{{ renameError }}</div> }
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
                  <button class="rename-btn" (click)="startRename(f)">Rename</button>
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
    .usage { margin-bottom: 14px; }
    .usage-text { display: flex; justify-content: space-between; color: var(--muted); font-size: 13px; margin-bottom: 6px; }
    .bar { height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; }
    .fill { height: 100%; background: var(--accent, #4dabf7); }
    .fill.warn { background: var(--danger); }
    .tools { display: flex; gap: 10px; margin-top: 14px; }
    .tools input { flex: 1 1 auto; width: auto; min-width: 0; }
    .tools select { flex: none; width: 190px; }
    .count { margin: 10px 0 0; }
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
    .rename-btn { color: var(--muted); }
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
  storage: StorageInfo | null = null;
  search = '';
  sortKey: SortKey = 'newest';
  fmt = formatBytes;

  /** What the list shows: search first, then sort. Recomputed on every change-detection pass; the lists are small. */
  get visible(): FileMeta[] {
    return sortFiles(filterFiles(this.files, this.search), this.sortKey);
  }

  get pct(): number {
    return this.storage ? percentUsed(this.storage.used_bytes, this.storage.quota_bytes) : 0;
  }

  picked: File | null = null;
  uploadPassword = '';
  uploading = false;
  uploadError = '';
  uploadOk = '';

  decrypting: string | null = null;
  downloadPassword = '';
  downloadError = '';
  busy = false;

  renaming: string | null = null;
  renameValue = '';
  renameError = '';
  renameNotice = '';

  confirmingDelete: string | null = null;
  deleteError = '';
  listNotice = '';

  async ngOnInit() {
    await this.refresh();
  }

  async refresh() {
    this.loading = true;
    try {
      [this.files, this.storage] = await Promise.all([this.filesApi.list(), this.filesApi.storage()]);
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
    this.renameNotice = '';
    this.listNotice = '';   // an old "Deleted ..." message shouldn't linger once the user does something else
    if (!this.picked) { this.uploadError = 'Choose a file to upload first.'; return; }
    if (this.storage && this.picked.size > this.storage.max_upload_bytes) {
      this.uploadError = `"${this.picked.name}" is ${formatBytes(this.picked.size)}. The limit is ${formatBytes(this.storage.max_upload_bytes)} per file.`;
      return;
    }
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

  startRename(f: FileMeta) {
    this.decrypting = null;
    this.confirmingDelete = null;
    this.listNotice = '';
    this.renameNotice = '';
    this.renameError = '';
    this.renameValue = f.filename;
    this.renaming = f.hash;
  }

  cancelRename() {
    this.renaming = null;
    this.renameError = '';
  }

  async saveRename(f: FileMeta) {
    this.renameError = '';
    const check = cleanFilename(this.renameValue);
    if (!check.ok) { this.renameError = check.error; return; }
    if (check.value === f.filename) { this.cancelRename(); return; }   // nothing changed, nothing to send
    this.busy = true;
    try {
      await this.filesApi.rename(f.hash, check.value);
      this.renaming = null;
      this.renameNotice = `Renamed "${f.filename}" to "${check.value}".`;
      await this.refresh();
    } catch (err) {
      const e = err as HttpErrorResponse;
      if (e.status === 404) { this.renameError = 'That file no longer exists.'; await this.refresh(); }
      else if (e.status === 422 && typeof e.error?.detail === 'string') this.renameError = e.error.detail;
      else this.renameError = "Couldn't rename this file. Nothing was changed — please try again.";
    } finally {
      this.busy = false;
    }
  }

  startDecrypt(f: FileMeta) {
    this.confirmingDelete = null;
    this.renaming = null;
    this.listNotice = '';
    this.renameNotice = '';
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
    this.renaming = null;
    this.renameNotice = '';
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
