import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import { pages, type PageId } from './app/pages';
import './styles.css';

const root = document.getElementById('root')!;
const page = pages.find(p => p.path === root.dataset.page)?.path ?? 'forecast';
ReactDOM.createRoot(root).render(<React.StrictMode><App page={page as PageId} /></React.StrictMode>);
