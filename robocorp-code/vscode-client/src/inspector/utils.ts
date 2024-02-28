// generateID - generates safe path IDs
export const generateID = (): string => {
    const prefix = `${Math.floor(Math.random() * 9000) + 1000}`; // this creates a 4 digit number
    const middle = `${Date.now()}`.replace(/(.{2})/g, "$1-"); // this will split the number up into groups of two or one
    const suffix = `${Math.floor(Math.random() * 9000) + 1000}`; // this creates a 4 digit number
    return `${prefix}-${middle}-${suffix}`;
};
