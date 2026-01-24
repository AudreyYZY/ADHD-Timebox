export const rewardMessages = {
  started: [
    "You showed up. That matters.",
    "Starting is the hardest part. You did it.",
    "You're here. That's enough for now.",
    "One step at a time.",
    "You chose to begin. That takes courage.",
  ],
  survived: [
    "You stayed with it. That's real.",
    "This still counts.",
    "You didn't disappear. That matters.",
    "Time spent trying is never wasted.",
    "You made it through.",
  ],
  admittedDifficulty: [
    "Honesty takes strength.",
    "You listened to yourself.",
    "Knowing when it's hard is wisdom.",
    "It's okay to struggle.",
    "You noticed something important.",
  ],
  choseRest: [
    "Rest is productive too.",
    "You chose yourself. Good.",
    "Stopping safely is a skill.",
    "You can come back when ready.",
    "Taking care of yourself matters.",
  ],
  partialProgress: [
    "Some is more than none.",
    "Progress isn't always linear.",
    "Every bit counts.",
    "You moved forward, even a little.",
    "Partial is still progress.",
  ],
  gotStuck: [
    "Stuck is information, not failure.",
    "Sometimes we need to pause.",
    "This tells you something useful.",
    "It's okay. Really.",
    "You tried. That's what matters.",
  ],
};

export function getRandomReward(
  type: keyof typeof rewardMessages
): string {
  const messages = rewardMessages[type];
  return messages[Math.floor(Math.random() * messages.length)];
}
