"""Space Invaders game implementation using ALE."""
import gymnasium as gym
from pathlib import Path
from typing import Optional, Tuple, Any
from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack
from stable_baselines3.common.atari_wrappers import (
    NoopResetEnv,
    MaxAndSkipEnv,
    EpisodicLifeEnv,
    FireResetEnv,
    ClipRewardEnv
)
from loguru import logger

from cli.games.base import GameInterface, GameConfig, EvaluationResult, ProgressCallback

# Optional NEAR imports
try:
    from cli.core.near import NEARWallet
    from cli.core.stake import StakeRecord
    NEAR_AVAILABLE = True
except ImportError:
    NEAR_AVAILABLE = False
    NEARWallet = Any  # Type alias for type hints

class SpaceInvadersGame(GameInterface):
    """Space Invaders game implementation."""
    
    def __call__(self):
        """Make the class callable to return itself."""
        return self
    
    @property
    def name(self) -> str:
        return "space_invaders"
        
    @property
    def env_id(self) -> str:
        return "ALE/SpaceInvaders-v5"
        
    @property
    def description(self) -> str:
        return "Defend Earth from alien invasion"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def score_range(self) -> tuple[float, float]:
        return (0, 1000)  # Space Invaders typical score range
        
    def get_score_range(self) -> tuple[float, float]:
        """Get valid score range for the game."""
        return self.score_range
        
    def make_env(self):
        """Create the game environment."""
        env = gym.make(self.env_id, render_mode='rgb_array')
        env = gym.wrappers.ResizeObservation(env, (84, 84))
        env = gym.wrappers.GrayscaleObservation(env)
        env = gym.wrappers.FrameStackObservation(env, 4)
        return env
        
    def load_model(self, model_path: str):
        """Load a trained model."""
        return DQN.load(model_path)
        
    def get_default_config(self) -> GameConfig:
        """Get default configuration for the game."""
        return GameConfig(
            total_timesteps=1_000_000,
            learning_rate=0.00025,
            buffer_size=250_000,
            learning_starts=50_000,
            batch_size=256,
            exploration_fraction=0.2,
            target_update_interval=2000,
            frame_stack=4
        )
    
    def _make_env(self, render: bool = False, record: bool = False) -> gym.Env:
        """Create the Space Invaders environment with proper wrappers."""
        # Use human rendering only when explicitly requested
        render_mode = "human" if render else "rgb_array"
        env = gym.make(self.env_id, render_mode=render_mode, frameskip=4)
        
        # Add standard Atari wrappers
        env = NoopResetEnv(env, noop_max=30)
        env = MaxAndSkipEnv(env, skip=4)
        env = EpisodicLifeEnv(env)
        env = FireResetEnv(env)
        env = ClipRewardEnv(env)  # Add reward clipping for stability
        
        # Observation preprocessing
        env = gym.wrappers.ResizeObservation(env, (84, 84))
        env = gym.wrappers.GrayscaleObservation(env, keep_dim=False)
        env = gym.wrappers.FrameStackObservation(env, 4)
        
        # Add video recording only when explicitly requested
        if record and not render:
            env = gym.wrappers.RecordVideo(
                env,
                "videos/training",
                episode_trigger=lambda x: x % 100 == 0  # Record every 100th episode
            )
        
        return env
    
    def train(self, render: bool = False, config_path: Optional[Path] = None) -> Path:
        """Train a Space Invaders agent."""
        config = self.load_config(config_path)
        
        # Create vectorized environment without recording
        env = DummyVecEnv([lambda: self._make_env(render, record=False) for _ in range(4)])  # Use 4 envs for stability
        env = VecFrameStack(env, config.frame_stack)
        
        # Create and train the model with optimized parameters for faster learning
        model = DQN(
            "CnnPolicy",
            env,
            learning_rate=0.0001,  # Reduced learning rate for stability
            buffer_size=50000,     # Smaller buffer for memory efficiency
            learning_starts=1000,   # Start learning very early
            batch_size=32,         # Small batches for faster updates
            exploration_fraction=0.1,  # Faster exploration decay
            target_update_interval=1000,  # More frequent target updates
            tensorboard_log="./tensorboard/space_invaders",
            verbose=1,
            train_freq=4,          # Update every 4 steps
            gradient_steps=1,      # One gradient step per update
            exploration_initial_eps=1.0,
            exploration_final_eps=0.05,  # Lower final exploration
            max_grad_norm=10,
            device='auto',
            policy_kwargs={
                "net_arch": [256, 128],  # Smaller network architecture
                "normalize_images": True  # Normalize inputs for stability
            }
        )
        
        # Reduce total timesteps for faster training
        total_timesteps = 250000  # ~30-45 minutes of training
        
        logger.info(f"Training Space Invaders agent for {total_timesteps} timesteps...")
        logger.info("This training should take about 30-45 minutes.")
        logger.info("Monitor progress in TensorBoard: tensorboard --logdir ./tensorboard")
        
        # Use our custom ProgressCallback for consistent progress tracking
        callback = ProgressCallback(total_timesteps)
        
        try:
            model.learn(
                total_timesteps=total_timesteps,
                callback=callback,
                progress_bar=True,
                log_interval=100
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
        
        # Save the model
        model_path = Path("models/space_invaders_final.zip")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(model_path))
        logger.info(f"Model saved to {model_path}")
        
        return model_path
    
    def evaluate(self, model_path: Path, episodes: int = 10, record: bool = False) -> EvaluationResult:
        """Evaluate a trained Space Invaders model."""
        env = DummyVecEnv([lambda: self._make_env(record)])
        env = VecFrameStack(env, 4)
        
        model = DQN.load(model_path, env=env)
        
        total_score = 0
        episode_lengths = []
        best_score = float('-inf')
        successes = 0
        
        for episode in range(episodes):
            obs = env.reset()[0]
            done = False
            episode_score = 0
            episode_length = 0
            
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, _ = env.step(action)
                episode_score += reward[0]
                episode_length += 1
                done = terminated[0] or truncated[0]
            
            total_score += episode_score
            episode_lengths.append(episode_length)
            best_score = max(best_score, episode_score)
            if episode_score > 100:  # Consider scoring over 100 as success
                successes += 1
        
        return EvaluationResult(
            score=total_score / episodes,
            episodes=episodes,
            success_rate=successes / episodes,
            best_episode_score=best_score,
            avg_episode_length=sum(episode_lengths) / len(episode_lengths)
        )
    
    def validate_model(self, model_path: Path) -> bool:
        """Validate Space Invaders model file."""
        try:
            env = DummyVecEnv([lambda: self._make_env()])
            DQN.load(model_path, env=env)
            return True
        except Exception as e:
            logger.error(f"Invalid model file: {e}")
            return False
    
    async def stake(self, wallet: NEARWallet, model_path: Path, amount: float, target_score: float) -> None:
        """Stake NEAR on Space Invaders performance."""
        if not NEAR_AVAILABLE:
            raise RuntimeError("NEAR integration not available")
            
        if not wallet.is_logged_in():
            raise ValueError("Must be logged in to stake")
        
        if not self.validate_model(model_path):
            raise ValueError("Invalid model file")
        
        # Verify target score is within range
        min_score, max_score = self.score_range
        if not min_score <= target_score <= max_score:
            raise ValueError(f"Target score must be between {min_score} and {max_score}")
        
        # Use staking module
        await stake_on_game(
            wallet=wallet,
            game_name=self.name,
            model_path=model_path,
            amount=amount,
            target_score=target_score,
            score_range=self.score_range
        )

def register():
    """Register the Space Invaders game."""
    from cli.games import register_game
    register_game(SpaceInvadersGame) 