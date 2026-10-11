import {afterEach,vi} from 'vitest';
import {cleanup} from '@testing-library/react';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
Object.defineProperty(window,'matchMedia',{writable:true,value:query=>({matches:query.includes('reduced-motion'),media:query,addEventListener(){},removeEventListener(){}})});
