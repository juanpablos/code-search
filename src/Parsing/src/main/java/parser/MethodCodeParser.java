package parser;

import com.github.javaparser.JavaParser;
import com.github.javaparser.JavaToken;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.ast.stmt.*;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;
import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.StreamSupport;

public class MethodCodeParser {

    public static void main(String[] args) {
        System.out.println(parseMethod(args[0]));
    }

    /**
     * Parse and tokenize a java method represented as a string.
     * Used as a worker to generate input strings to the consumer method in python
     *
     * @param code java method represented as a string
     * @return an object that represents the tokenized version of the input method
     */
    public static MethodContainer parseMethod(String code) {

        MethodContainer container = new MethodContainer();

        // The input code must be wrapped in a class in order to be parsed correctly
        CompilationUnit cu = JavaParser.parse("class A {" + code + "}");

        for (MethodDeclaration method : cu.findAll(MethodDeclaration.class)) {
            // tokenize method name
            String methodName = method.getNameAsString();
            List<String> nameList = Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(methodName));
            nameList.forEach(token -> container.addNameToken(token.toLowerCase()));

            // Body
            if (method.getBody().isPresent()) {
                // tokenize
                // only filter for kind=89 -> identifier
                if (method.getBody().get().getTokenRange().isPresent()) {
                    Set<String> bodyTokens = new HashSet<>();
                    StreamSupport.<JavaToken>stream(method.getBody().get().getTokenRange().get().spliterator(), false)
                            .filter(token -> token.getKind() == 89)
                            .forEach(t -> bodyTokens.addAll(Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(t.asString()))));

                    bodyTokens.forEach(token -> container.addBodyToken(token.toLowerCase()));
                }

                // Sequence api calls
                // BlockStmnt
                method.getBody().get().accept(new APICallsVisitor(), container);
            }
        }

        return container;
    }


    /**
     * Just a visitor class to extract the api call in the desired order
     */
    private static class APICallsVisitor extends VoidVisitorAdapter<MethodContainer> {
        @Override
        public void visit(MethodCallExpr n, MethodContainer arg) {
            n.getArguments().forEach(p -> p.accept(this, arg));
            n.getScope().ifPresent(l -> l.accept(this, arg));
            n.getName().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));

            arg.addApiCall(n.getName().asString());
        }

        @Override
        public void visit(CatchClause n, MethodContainer arg) {
            n.getParameter().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(DoStmt n, MethodContainer arg) {
            n.getBody().accept(this, arg);
            n.getCondition().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(FieldAccessExpr n, MethodContainer arg) {
            n.getScope().accept(this, arg);
            n.getName().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ForeachStmt n, MethodContainer arg) {
            n.getIterable().accept(this, arg);
            n.getVariable().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ForStmt n, MethodContainer arg) {
            n.getInitialization().forEach(p -> p.accept(this, arg));
            n.getCompare().ifPresent(l -> l.accept(this, arg));
            n.getUpdate().forEach(p -> p.accept(this, arg));
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(SwitchStmt n, MethodContainer arg) {
            n.getSelector().accept(this, arg);
            n.getEntries().forEach(p -> p.accept(this, arg));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(SynchronizedStmt n, MethodContainer arg) {
            n.getExpression().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(TryStmt n, MethodContainer arg) {
            n.getResources().forEach(p -> p.accept(this, arg));
            n.getTryBlock().accept(this, arg);
            n.getCatchClauses().forEach(p -> p.accept(this, arg));
            n.getFinallyBlock().ifPresent(l -> l.accept(this, arg));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(WhileStmt n, MethodContainer arg) {
            n.getCondition().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(LambdaExpr n, MethodContainer arg) {
            n.getParameters().forEach(p -> p.accept(this, arg));
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(MethodReferenceExpr n, MethodContainer arg) {
            n.getScope().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ObjectCreationExpr n, MethodContainer arg) {
            // TODO: do we need this?
            //arg.add(n.getType().asString());
            super.visit(n, arg);
        }
    }
}
