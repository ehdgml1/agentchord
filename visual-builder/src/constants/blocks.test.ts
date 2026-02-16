import { describe, it, expect } from 'vitest';
import { BlockType } from '../types/blocks';
import {
  BLOCK_DEFINITIONS,
  getBlockDefinition,
  getPaletteBlocks,
  supportsMultipleInputs,
  supportsMultipleOutputs,
} from './blocks';

describe('blocks constants', () => {
  describe('BLOCK_DEFINITIONS', () => {
    it('should have 8 entries', () => {
      expect(BLOCK_DEFINITIONS).toHaveLength(8);
    });

    it('should include agent type', () => {
      const agentDef = BLOCK_DEFINITIONS.find(
        (def) => def.type === BlockType.AGENT
      );
      expect(agentDef).toBeDefined();
    });

    it('should include mcp_tool type', () => {
      const mcpToolDef = BLOCK_DEFINITIONS.find(
        (def) => def.type === BlockType.MCP_TOOL
      );
      expect(mcpToolDef).toBeDefined();
    });

    it('should include parallel type', () => {
      const parallelDef = BLOCK_DEFINITIONS.find(
        (def) => def.type === BlockType.PARALLEL
      );
      expect(parallelDef).toBeDefined();
    });

    it('should include condition type', () => {
      const conditionDef = BLOCK_DEFINITIONS.find(
        (def) => def.type === BlockType.CONDITION
      );
      expect(conditionDef).toBeDefined();
    });

    it('should include feedback_loop type', () => {
      const feedbackLoopDef = BLOCK_DEFINITIONS.find(
        (def) => def.type === BlockType.FEEDBACK_LOOP
      );
      expect(feedbackLoopDef).toBeDefined();
    });

    it('should have required fields in each definition', () => {
      BLOCK_DEFINITIONS.forEach((def) => {
        expect(def).toHaveProperty('type');
        expect(def).toHaveProperty('label');
        expect(def).toHaveProperty('description');
        expect(def).toHaveProperty('icon');
        expect(def).toHaveProperty('color');
        expect(def).toHaveProperty('defaultData');
        expect(typeof def.type).toBe('string');
        expect(typeof def.label).toBe('string');
        expect(typeof def.description).toBe('string');
        expect(typeof def.icon).toBe('string');
        expect(typeof def.color).toBe('string');
        expect(typeof def.defaultData).toBe('object');
      });
    });
  });

  describe('getBlockDefinition', () => {
    it('should return correct definition for agent type', () => {
      const def = getBlockDefinition(BlockType.AGENT);
      expect(def).toBeDefined();
      expect(def?.type).toBe(BlockType.AGENT);
      expect(def?.label).toBe('Agent');
    });

    it('should return undefined for invalid type', () => {
      const def = getBlockDefinition('invalid_type' as BlockType);
      expect(def).toBeUndefined();
    });
  });

  describe('getPaletteBlocks', () => {
    it('should return all definitions (no START/END in BLOCK_DEFINITIONS)', () => {
      const paletteBlocks = getPaletteBlocks();
      expect(paletteBlocks).toHaveLength(8);
      expect(paletteBlocks).toEqual(BLOCK_DEFINITIONS);
    });
  });

  describe('supportsMultipleInputs', () => {
    it('should return true for agent', () => {
      expect(supportsMultipleInputs(BlockType.AGENT)).toBe(true);
    });

    it('should return true for condition', () => {
      expect(supportsMultipleInputs(BlockType.CONDITION)).toBe(true);
    });

    it('should return false for parallel', () => {
      expect(supportsMultipleInputs(BlockType.PARALLEL)).toBe(false);
    });

    it('should return false for feedback_loop', () => {
      expect(supportsMultipleInputs(BlockType.FEEDBACK_LOOP)).toBe(false);
    });

    it('should return true for mcp_tool', () => {
      expect(supportsMultipleInputs(BlockType.MCP_TOOL)).toBe(true);
    });
  });

  describe('supportsMultipleOutputs', () => {
    it('should return true for condition', () => {
      expect(supportsMultipleOutputs(BlockType.CONDITION)).toBe(true);
    });

    it('should return true for parallel', () => {
      expect(supportsMultipleOutputs(BlockType.PARALLEL)).toBe(true);
    });

    it('should return false for agent', () => {
      expect(supportsMultipleOutputs(BlockType.AGENT)).toBe(false);
    });

    it('should return false for mcp_tool', () => {
      expect(supportsMultipleOutputs(BlockType.MCP_TOOL)).toBe(false);
    });

    it('should return false for feedback_loop', () => {
      expect(supportsMultipleOutputs(BlockType.FEEDBACK_LOOP)).toBe(false);
    });
  });
});
