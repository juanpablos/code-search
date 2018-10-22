package parser;

import com.github.javaparser.JavaParser;
import com.github.javaparser.JavaToken;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.ast.stmt.*;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.StreamSupport;

public class Main {

    public static void main(String[] args) {
        String nameFile = "names.txt";
        String apiFile = "api.txt";
        String tokenFile = "tokens.txt";
        String commentFile = "comments.txt";

        File startPath = new File(".");
        for (File file : Objects.requireNonNull(startPath.listFiles())) {
            if (file.isDirectory()) {
                forEachJavaFile(file, commentFile, nameFile, apiFile, tokenFile);
            }
        }
    }

    private static void forEachJavaFile(File directory, String commentFile, String methodNameFile, String apiFile, String tokenFile) {
        List<File> files = (List<File>) FileUtils.listFiles(directory, new String[]{"java"}, true);
        for (File file : files) {
            parseMethods(commentFile, methodNameFile, apiFile, tokenFile, file);
        }
    }

    private static void parseMethods(String commentFile, String methodNameFile, String apiFile, String tokenFile, File inputFile) {

        try (Writer names = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(methodNameFile), StandardCharsets.UTF_8));
             Writer apiCalls = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(apiFile), StandardCharsets.UTF_8));
             Writer tokens = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(tokenFile), StandardCharsets.UTF_8));
             Writer comments = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(commentFile), StandardCharsets.UTF_8));
             FileInputStream in = new FileInputStream(inputFile)) {

            CompilationUnit cu = JavaParser.parse(in);

            for (MethodDeclaration method : cu.findAll(MethodDeclaration.class)) {
                // write the method name
                String methodName = method.getNameAsString();
                List<String> nameList = Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(methodName));
                names.write(String.join(" ", nameList).toLowerCase());
                names.write("\n");

                // Write javadoc comment
                if (method.getJavadoc().isPresent()) {
                    String firstLine = method.getJavadoc().get().getDescription().toText().split("\\r?\\n")[0];
                    comments.write(firstLine.toLowerCase());
                    comments.write("\n");
                } else {
                    comments.write("\n");
                }

                // Body
                if (method.getBody().isPresent()) {
                    // tokenize
                    // only filter for kind=89 -> identifier
                    if (method.getBody().get().getTokenRange().isPresent()) {
                        Set<String> bodyTokens = new HashSet<>();
                        StreamSupport.<JavaToken>stream(method.getBody().get().getTokenRange().get().spliterator(), false)
                                .filter(token -> token.getKind() == 89)
                                .forEach(t -> bodyTokens.addAll(Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(t.asString()))));

                        tokens.write(String.join(" ", bodyTokens).toLowerCase());
                        tokens.write("\n");
                    } else {
                        tokens.write("\n");
                    }

                    // Sequence api calls
                    List<String> sequenceAPI = new ArrayList<>();
                    // BlockStmnt
                    method.getBody().get().accept(new APICallsVisitor(), sequenceAPI);
                    apiCalls.write(String.join(" ", sequenceAPI));
                    apiCalls.write("\n");
                } else {
                    tokens.write("\n");
                    apiCalls.write("\n");
                }
            }
        } catch (IOException e) {
            System.out.println("Error");
        }
    }

    private static class APICallsVisitor extends VoidVisitorAdapter<List<String>> {
        @Override
        public void visit(MethodCallExpr n, List<String> arg) {
            n.getArguments().forEach(p -> p.accept(this, arg));
            n.getScope().ifPresent(l -> l.accept(this, arg));
            n.getName().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));

            arg.add(n.getName().asString());
        }

        @Override
        public void visit(CatchClause n, List<String> arg) {
            n.getParameter().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(DoStmt n, List<String> arg) {
            n.getBody().accept(this, arg);
            n.getCondition().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(FieldAccessExpr n, List<String> arg) {
            n.getScope().accept(this, arg);
            n.getName().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ForeachStmt n, List<String> arg) {
            n.getIterable().accept(this, arg);
            n.getVariable().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ForStmt n, List<String> arg) {
            n.getInitialization().forEach(p -> p.accept(this, arg));
            n.getCompare().ifPresent(l -> l.accept(this, arg));
            n.getUpdate().forEach(p -> p.accept(this, arg));
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(SwitchStmt n, List<String> arg) {
            n.getSelector().accept(this, arg);
            n.getEntries().forEach(p -> p.accept(this, arg));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(SynchronizedStmt n, List<String> arg) {
            n.getExpression().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(TryStmt n, List<String> arg) {
            n.getResources().forEach(p -> p.accept(this, arg));
            n.getTryBlock().accept(this, arg);
            n.getCatchClauses().forEach(p -> p.accept(this, arg));
            n.getFinallyBlock().ifPresent(l -> l.accept(this, arg));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(WhileStmt n, List<String> arg) {
            n.getCondition().accept(this, arg);
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(LambdaExpr n, List<String> arg) {
            n.getParameters().forEach(p -> p.accept(this, arg));
            n.getBody().accept(this, arg);
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(MethodReferenceExpr n, List<String> arg) {
            n.getScope().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));
        }

        @Override
        public void visit(ObjectCreationExpr n, List<String> arg) {
            // TODO: do we need this?
            //arg.add(n.getType().asString());
            super.visit(n, arg);
        }
    }
}
