import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterOutlet, RouterLink, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { DashboardComponent } from './dashboard/dashboard.component';
import { SidebarComponent } from './sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, DashboardComponent, SidebarComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  title = 'Weak Signal Intelligence';
  // UI State
  showConfig = signal(true);

  internalSignals = signal<any[]>([]);
  externalSignals = signal<any[]>([]);
  futureBusinessImpact = signal<any>(null);
  whyChain = signal<any>(null);
  uploading = signal(false);
  loadingExternal = signal(false);
  error = signal<string | null>(null);

  constructor(private http: HttpClient, private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      this.showConfig.set(event.url !== '/dashboard');
    });
  }

  ngOnInit() {
    this.showConfig.set(this.router.url !== '/dashboard');
    this.loadAllSignals();
  }

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
        this.futureBusinessImpact.set(response.future_business_impact || null);
        this.whyChain.set(response.why_chain || null);
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
        this.internalSignals.set(response.internal_signals || response.internal || []);
        this.externalSignals.set(response.external_signals || response.external || []);
        this.futureBusinessImpact.set(response.future_business_impact || response.future_impact || null);
        this.whyChain.set(response.why_chain || null);
      },
      error: (err: any) => console.error('Failed to load signals', err)
    });
  }

}
