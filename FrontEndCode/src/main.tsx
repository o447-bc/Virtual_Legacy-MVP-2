import { createRoot } from 'react-dom/client'
import { Amplify } from 'aws-amplify'
import App from './App.tsx'
import './index.css'
import { awsConfig } from './aws-config'

Amplify.configure(awsConfig)

createRoot(document.getElementById("root")!).render(<App />);
