export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export function timeInMillis(): number {
    return new Date().getTime()
};

export class Timing {
    initialTime: number;
    currentTime: number;
    constructor() {
        this.initialTime = timeInMillis();
        this.currentTime = this.initialTime;
    }
    
    elapsedFromLastMeasurement(timeToCheck: number) {
        let curr: number = timeInMillis();
        if(curr - this.currentTime > timeToCheck){
            this.currentTime = curr;
            return true;
        }
        return false;
    }
    
    getTotalElapsedAsStr() {
        return ((timeInMillis() - this.initialTime) / 1000).toFixed(1) + 's';
    }
}