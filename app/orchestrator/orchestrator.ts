/**
 * Orchestrator - 时间盒系统编排器
 *
 * 职责：
 * - 维护应用状态
 * - 决定何时调用 Decision Agent
 * - 将 Agent 输出转换为前端状态
 *
 * 接收事件：
 * - APP_START: 应用启动
 * - TIMEBOX_STARTED: 时间盒开始
 * - TIMEBOX_ENDED: 时间盒结束
 * - TIMEBOX_INTERRUPTED: 时间盒被中断
 * - REQUEST_NEW: 请求新推荐
 */

import {
  OrchestratorState,
  OrchestratorEvent,
  OrchestratorOutput,
  ORCHESTRATOR_EVENTS,
  TimeBox,
  TimeBoxOutcome,
  TimeBoxRecommendation,
  DecisionAgentContext,
  Task,
} from "../types";
import { IDecisionAgent, decisionAgent } from "../agents/decisionAgent";
import { api } from "../utils/api";

// 初始状态
export const initialOrchestratorState: OrchestratorState = {
  activeTimeBox: null,
  recommendation: null,
  outcomes: [],
  tasks: [],
  isLoadingRecommendation: false,
};

/**
 * Orchestrator 类
 */
export class Orchestrator {
  private agent: IDecisionAgent;

  constructor(agent: IDecisionAgent = decisionAgent) {
    this.agent = agent;
  }

  /**
   * 处理事件 - 主入口
   */
  async handleEvent(event: OrchestratorEvent): Promise<OrchestratorOutput> {
    switch (event.event) {
      case ORCHESTRATOR_EVENTS.APP_START:
        return this.handleAppStart(event);

      case ORCHESTRATOR_EVENTS.TIMEBOX_STARTED:
        return this.handleTimeBoxStarted(event);

      case ORCHESTRATOR_EVENTS.TIMEBOX_ENDED:
        return this.handleTimeBoxEnded(event);

      case ORCHESTRATOR_EVENTS.TIMEBOX_INTERRUPTED:
        return this.handleTimeBoxInterrupted(event);

      case ORCHESTRATOR_EVENTS.REQUEST_NEW:
        return this.handleRequestNew(event);

      default:
        // TypeScript 会确保这不会发生
        const _exhaustiveCheck: never = event;
        throw new Error(`未处理的事件类型: ${(_exhaustiveCheck as any).event}`);
    }
  }

  /**
   * APP_START 事件处理
   * - 如果没有活跃的时间盒，调用 Decision Agent
   * - 保存推荐
   */
  private async handleAppStart(
    event: Extract<OrchestratorEvent, { event: typeof ORCHESTRATOR_EVENTS.APP_START }>
  ): Promise<OrchestratorOutput> {
    const { payload, state } = event;
    let newState: OrchestratorState = {
      ...state,
      tasks: payload.tasks,
    };

    // 如果没有活跃的时间盒，请求推荐
    if (!newState.activeTimeBox && payload.tasks.length > 0) {
      newState = { ...newState, isLoadingRecommendation: true };

      try {
        const recommendation = await this.callDecisionAgent(newState);
        newState = {
          ...newState,
          recommendation,
          isLoadingRecommendation: false,
        };
      } catch (error) {
        console.error("Failed to get recommendation on APP_START:", error);
        newState = { ...newState, isLoadingRecommendation: false };
      }
    }

    return { newState };
  }

  /**
   * TIMEBOX_STARTED 事件处理
   * - 设置 activeTimeBox
   * - 清除 recommendation
   */
  private async handleTimeBoxStarted(
    event: Extract<OrchestratorEvent, { event: typeof ORCHESTRATOR_EVENTS.TIMEBOX_STARTED }>
  ): Promise<OrchestratorOutput> {
    const { payload, state } = event;

    const activeTimeBox: TimeBox = {
      id: this.generateId(),
      taskId: payload.taskId,
      durationMinutes: payload.durationMinutes,
      startedAt: new Date().toISOString(),
    };

    const newState: OrchestratorState = {
      ...state,
      activeTimeBox,
      recommendation: null, // 清除推荐
    };

    return { newState };
  }

  /**
   * TIMEBOX_ENDED 事件处理
   * - 清除 activeTimeBox
   * - 保存 outcome
   * - 调用 Decision Agent
   * - 保存新推荐
   */
  private async handleTimeBoxEnded(
    event: Extract<OrchestratorEvent, { event: typeof ORCHESTRATOR_EVENTS.TIMEBOX_ENDED }>
  ): Promise<OrchestratorOutput> {
    const { payload, state } = event;

    const updatedTasks = state.tasks.map((task) =>
      task.id === payload.taskId ? { ...task, status: "completed" } : task
    );

    // 创建结果记录
    const outcome: TimeBoxOutcome = {
      timeBoxId: state.activeTimeBox?.id || this.generateId(),
      taskId: payload.taskId,
      durationMinutes: payload.durationMinutes,
      actualMinutes: payload.actualMinutes,
      outcome: "completed",
      endedAt: new Date().toISOString(),
    };

    let newState: OrchestratorState = {
      ...state,
      activeTimeBox: null, // 清除活跃时间盒
      outcomes: [outcome, ...state.outcomes], // 保存结果
      tasks: updatedTasks,
      isLoadingRecommendation: true,
    };

    try {
      await api.updateTaskStatus(payload.taskId, "completed");
    } catch (error) {
      console.error("Failed to update task status:", error);
    }

    // 调用 Decision Agent 获取新推荐
    if (newState.tasks.length > 0) {
      try {
        const recommendation = await this.callDecisionAgent(newState);
        newState = {
          ...newState,
          recommendation,
          isLoadingRecommendation: false,
        };
      } catch (error) {
        console.error("Failed to get recommendation on TIMEBOX_ENDED:", error);
        newState = { ...newState, isLoadingRecommendation: false };
      }
    } else {
      newState = { ...newState, isLoadingRecommendation: false };
    }

    return { newState };
  }

  /**
   * TIMEBOX_INTERRUPTED 事件处理
   * - 清除 activeTimeBox
   * - 标记 outcome 为 interrupted
   * - 调用 Decision Agent（偏好低认知负荷）
   */
  private async handleTimeBoxInterrupted(
    event: Extract<OrchestratorEvent, { event: typeof ORCHESTRATOR_EVENTS.TIMEBOX_INTERRUPTED }>
  ): Promise<OrchestratorOutput> {
    const { payload, state } = event;

    // 创建中断结果记录
    const outcome: TimeBoxOutcome = {
      timeBoxId: state.activeTimeBox?.id || this.generateId(),
      taskId: payload.taskId,
      durationMinutes: payload.durationMinutes,
      actualMinutes: payload.elapsedMinutes,
      outcome: "interrupted",
      endedAt: new Date().toISOString(),
    };

    let newState: OrchestratorState = {
      ...state,
      activeTimeBox: null, // 清除活跃时间盒
      outcomes: [outcome, ...state.outcomes], // 保存中断结果
      isLoadingRecommendation: true,
    };

    // 调用 Decision Agent，偏好低认知负荷任务
    if (newState.tasks.length > 0) {
      try {
        const recommendation = await this.callDecisionAgent(
          newState,
          true // preferLowCognitiveLoad
        );
        newState = {
          ...newState,
          recommendation,
          isLoadingRecommendation: false,
        };
      } catch (error) {
        console.error("Failed to get recommendation on TIMEBOX_INTERRUPTED:", error);
        newState = { ...newState, isLoadingRecommendation: false };
      }
    } else {
      newState = { ...newState, isLoadingRecommendation: false };
    }

    return { newState };
  }

  /**
   * REQUEST_NEW 事件处理
   * - 调用 Decision Agent
   * - 替换推荐
   */
  private async handleRequestNew(
    event: Extract<OrchestratorEvent, { event: typeof ORCHESTRATOR_EVENTS.REQUEST_NEW }>
  ): Promise<OrchestratorOutput> {
    const { payload, state } = event;

    let newState: OrchestratorState = {
      ...state,
      isLoadingRecommendation: true,
    };

    if (newState.tasks.length > 0) {
      try {
        const recommendation = await this.callDecisionAgent(
          newState,
          payload.preferLowCognitiveLoad
        );
        newState = {
          ...newState,
          recommendation, // 替换推荐
          isLoadingRecommendation: false,
        };
      } catch (error) {
        console.error("Failed to get recommendation on REQUEST_NEW:", error);
        newState = { ...newState, isLoadingRecommendation: false };
      }
    } else {
      newState = { ...newState, isLoadingRecommendation: false };
    }

    return { newState };
  }

  /**
   * 调用 Decision Agent
   */
  private async callDecisionAgent(
    state: OrchestratorState,
    preferLowCognitiveLoad?: boolean
  ): Promise<TimeBoxRecommendation> {
    const context: DecisionAgentContext = {
      tasks: state.tasks,
      outcomes: state.outcomes,
      currentTime: new Date().toISOString(),
      preferLowCognitiveLoad,
    };

    return this.agent.recommend(context);
  }

  /**
   * 生成唯一 ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 更新任务池
   */
  updateTasks(state: OrchestratorState, tasks: Task[]): OrchestratorState {
    return {
      ...state,
      tasks,
    };
  }
}

// 默认导出单例实例
export const orchestrator = new Orchestrator();
