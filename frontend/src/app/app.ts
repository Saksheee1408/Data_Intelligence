import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'Weak Signal Intelligence';
  internalSignals = signal<any[]>([]);
  externalSignals = signal<any[]>([]);
  uploading = signal(false);
  loadingExternal = signal(false);
  error = signal<string | null>(null);

  constructor(private http: HttpClient) { }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.uploadFile(file);
    }
  }

  uploadFile(file: File) {
    this.uploading.set(true);
    this.error.set(null);

    const formData = new FormData();
    formData.append('file', file);

    this.http.post<any>('http://localhost:8000/upload/internal', formData).subscribe({
      next: (response: any) => {
        this.internalSignals.set(response.internal_signals || []);
        this.externalSignals.set(response.external_signals || []);
        this.uploading.set(false);
      },
      error: (err: any) => {
        console.error(err);
        this.error.set('Failed to upload file. Make sure the backend is running.');
        this.uploading.set(false);
      }
    });
  }

  triggerExternalSensing() {
    this.loadingExternal.set(true);
    this.http.post<any>('http://localhost:8000/trigger/external', {}).subscribe({
      next: (response: any) => {
        this.loadAllSignals();
        this.loadingExternal.set(false);
      },
      error: (err: any) => {
        this.error.set('Failed to trigger external sensing.');
        this.loadingExternal.set(false);
      }
    });
  }

  loadAllSignals() {
    this.http.get<any>('http://localhost:8000/signals').subscribe({
      next: (response: any) => {
        this.internalSignals.set(response.internal || []);
        this.externalSignals.set(response.external || []);
      },
      error: (err: any) => console.error('Failed to load signals', err)
    });
  }

  ngOnInit() {
    this.loadAllSignals();
  }
}
