// TypeScript Compiler Integration
import * as ts from "typescript";

export type CompileResult = {
  success: boolean;
  output?: string;
  errors?: string[];
  diagnostics?: ts.Diagnostic[];
};

export class TypeScriptCompiler {
  private compilerOptions: ts.CompilerOptions;

  constructor() {
    this.compilerOptions = {
      target: ts.ScriptTarget.ES2020,
      module: ts.ModuleKind.ES2020,
      lib: ["ES2020", "DOM"],
      strict: true,
      esModuleInterop: true,
      skipLibCheck: true,
      moduleResolution: ts.ModuleResolutionKind.NodeJs,
      allowSyntheticDefaultImports: true,
      noEmit: false,
    };
  }

  compile(fileName: string, sourceCode: string): CompileResult {
    try {
      // Create a source file
      const sourceFile = ts.createSourceFile(
        fileName,
        sourceCode,
        ts.ScriptTarget.ES2020,
        true
      );

      // Transpile
      const result = ts.transpileModule(sourceCode, {
        compilerOptions: this.compilerOptions,
        fileName,
      });

      // Check for diagnostics
      if (result.diagnostics && result.diagnostics.length > 0) {
        const errors = result.diagnostics.map((d) => {
          const message = ts.flattenDiagnosticMessageText(d.messageText, "\n");
          return `${fileName}: ${message}`;
        });

        return {
          success: false,
          errors,
          diagnostics: result.diagnostics,
        };
      }

      return {
        success: true,
        output: result.outputText,
      };
    } catch (error) {
      return {
        success: false,
        errors: [error instanceof Error ? error.message : String(error)],
      };
    }
  }

  compileMultiple(files: Map<string, string>): Map<string, CompileResult> {
    const results = new Map<string, CompileResult>();

    for (const [fileName, sourceCode] of files.entries()) {
      results.set(fileName, this.compile(fileName, sourceCode));
    }

    return results;
  }

  validate(sourceCode: string): { valid: boolean; errors: string[] } {
    const sourceFile = ts.createSourceFile(
      "temp.ts",
      sourceCode,
      ts.ScriptTarget.ES2020,
      true
    );

    const errors: string[] = [];

    // Simple syntax check
    function visit(node: ts.Node) {
      // Check for syntax errors
      if (node.kind === ts.SyntaxKind.Unknown) {
        errors.push("Syntax error detected");
      }
      ts.forEachChild(node, visit);
    }

    visit(sourceFile);

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  // Format code
  format(sourceCode: string): string {
    try {
      const sourceFile = ts.createSourceFile(
        "temp.ts",
        sourceCode,
        ts.ScriptTarget.ES2020,
        true
      );

      const printer = ts.createPrinter({
        newLine: ts.NewLineKind.LineFeed,
      });

      return printer.printFile(sourceFile);
    } catch {
      return sourceCode;
    }
  }
}

// Singleton instance
export const compiler = new TypeScriptCompiler();
