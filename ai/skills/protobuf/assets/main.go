// Package main adds the project's JSON string field rule to Buf lint.
package main

import (
	"context"
	"strings"

	"buf.build/go/bufplugin/check"
	"buf.build/go/bufplugin/check/checkutil"
	"google.golang.org/protobuf/reflect/protoreflect"
)

func main() {
	check.Main(&check.Spec{
		Rules: []*check.RuleSpec{{
			ID:      "FIELD_NO_JSON_STRING",
			Default: true,
			Purpose: "Rejects string fields ending in _json; structured data belongs in typed messages.",
			Type:    check.RuleTypeLint,
			Handler: checkutil.NewFieldRuleHandler(checkJSONField, checkutil.WithoutImports()),
		}},
	})
}

func checkJSONField(_ context.Context, response check.ResponseWriter, _ check.Request, field protoreflect.FieldDescriptor) error {
	if field.Kind() == protoreflect.StringKind && strings.HasSuffix(string(field.Name()), "_json") {
		response.AddAnnotation(
			check.WithDescriptor(field),
			check.WithMessagef("String field %q ends in _json; define typed message fields instead of serializing JSON.", field.FullName()),
		)
	}
	return nil
}
